import sqlite3
import streamlit as st
import re, time, json
import pandas as pd

from .constants import SQLITE_DB, DB_SIMULATION_MASTER_TABLE, DB_EXPERIMENT_CONFIG_TABLE


def get_db_conn():
    """
    This function returns a connection object to a SQLite database.
    @returns The function `get_db_conn()` is returning a connection object to a SQLite database
    specified by the constant `SQLITE_DB`.
    """
    conn = sqlite3.connect(database=SQLITE_DB, isolation_level=None)  # auto-commit is enabled
    return conn


def db_query_fetch(query, params):
    """
    The function `db_query_fetch` executes an SQL query with parameters and returns the results as a
    list of dictionaries.
    @param query - a string containing the SQL query to be executed
    @param params - params is a tuple or list of parameters to be used in the SQL query. These
    parameters are used to replace placeholders in the query string to prevent SQL injection attacks and
    to ensure that the query is executed correctly.
    @returns The function `db_query_fetch` returns a list of dictionaries containing the results of a
    database query.
    """
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        res = cur.execute(query, params)
        colname = [ d[0] for d in res.description ]
        data = [ dict(zip(colname, r)) for r in res.fetchall() ]
        cur.close()
        return data
    except Exception as e:
        raise e
    finally:
        conn.close()

def db_query_execute(query, params):
    """
    This function executes a database query with parameters and handles exceptions and transactions.
    @param query - a string containing the SQL query to be executed
    @param params - params is a tuple or dictionary containing the values to be substituted in the
    query. These values are used to prevent SQL injection attacks and to ensure that the query is
    executed correctly. The values are substituted in the query using placeholders, such as "?" or
    ":param_name".
    """
    conn = get_db_conn()
    try:
        res = conn.execute(query, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        

##############################
# Functions that perform CRUD operations on simulation
##############################

def get_simulation_table_name(sim_name: str):
    sim_table = 'sim_' + re.sub( re.compile(r'[^A-Za-z0-9]'), '_', sim_name.lower() )
    return sim_table


def create_simulation(sim_name: str):
    # create master table entry
    query = f"CREATE TABLE IF NOT EXISTS {DB_SIMULATION_MASTER_TABLE}(  \
        id INTEGER PRIMARY KEY AUTOINCREMENT, \
        name VARCHAR NOT NULL UNIQUE, \
        tablename VARCHAR NOT NULL, \
        createdat INTEGER NOT NULL \
    );"
    db_query_execute(query, ())

    # insert entry into master table
    sim_table = get_simulation_table_name(sim_name)
    query = f"INSERT INTO {DB_SIMULATION_MASTER_TABLE}(name, tablename, createdat) VALUES (?, ?, ?);"
    db_query_execute(query, (sim_name, sim_table, int(time.time()) ))
    return True

def insert_data_to_simulation(df: pd.DataFrame, sim_name: str, exp_num: int):
    sim_table = get_simulation_table_name(sim_name)
    df['experiment_num'] = exp_num
    if exp_num == 0:
        # initial experiment, replace everything
        df.to_sql(sim_table, get_db_conn(), if_exists="replace", index=False)
    else:
        # table exists
        sql = f"DELETE FROM {sim_table} WHERE experiment_num = {exp_num};"
        db_query_execute(sql, ())

        # now append the data
        df.to_sql(sim_table, get_db_conn(), if_exists="append", index=False)
    return True

def insert_experiment_config(exp_conf: dict, results: dict, sim_name: str, exp_num: int):
    sql = f"CREATE TABLE IF NOT EXISTS {DB_EXPERIMENT_CONFIG_TABLE}(    \
        simulation_name VARCHAR NOT NULL, \
        experiment_num INTEGER NOT NULL , \
        config VARCHAR NOT NULL, \
        results VARCHAR NOT NULL,   \
        oncreatedat INTEGER NOT NULL \
    );"
    db_query_execute(sql, ())
    sql = f"DELETE FROM {DB_EXPERIMENT_CONFIG_TABLE} WHERE simulation_name = ? AND experiment_num = ?;"
    db_query_execute(sql, (sim_name, exp_num))
    sql = f"INSERT INTO {DB_EXPERIMENT_CONFIG_TABLE}(simulation_name, experiment_num, config, results, oncreatedat) VALUES (?, ?, ?, ?, ?);"
    db_query_execute(sql, (sim_name, exp_num, json.dumps(exp_conf), json.dumps(results), int(time.time()) ))


def list_simulations():
    sql = f"SELECT * FROM {DB_SIMULATION_MASTER_TABLE};"
    result = db_query_fetch(sql, ())
    return result


def get_simulation_suggestion(search_query: str):
    sql = f"SELECT * FROM {DB_SIMULATION_MASTER_TABLE} WHERE name LIKE ? LIMIT 5;"
    result = db_query_fetch(sql, ('%' + search_query + '%', ))
    return result

def delete_simulation(sim_name: str):
    sim_table = get_simulation_table_name(sim_name)
    sql = f"DROP TABLE {sim_table};"
    db_query_execute(sql, ())

    # delete from master table
    sql = f"DELETE FROM {DB_SIMULATION_MASTER_TABLE} WHERE tablename = ?;"
    db_query_execute(sql, (sim_table, ))
    return True

def get_simulation_data_snippet(sim_name: str, count = 5):
    sim_table = get_simulation_table_name(sim_name)
    sql = f"SELECT * FROM {sim_table} WHERE experiment_num = 0 ORDER BY TimeIndex ASC;"
    newdf = pd.read_sql(sql, get_db_conn(), index_col=None, parse_dates=['Time'])
    if newdf.shape[0] > (2 * count):
        return newdf.head(count), newdf.tail(count)
    else:
        return newdf, None
    

def get_experiment_count(sim_table: str):
    sql = f"SELECT MAX(experiment_num) as lastexp FROM {sim_table};"
    result = db_query_fetch(sql, ())
    if result is None or len(result) == 0:
        return 0
    else:
        return result[0].get('lastexp', 0)
    

def get_experiment_data(sim_name: str, exp_num: int):
    sim_table = get_simulation_table_name(sim_name)
    sql = f"SELECT * FROM {sim_table} WHERE experiment_num = {exp_num} ORDER BY TimeIndex ASC;"
    df = pd.read_sql(sql, get_db_conn(), index_col=None, parse_dates=['Time'])
    return df.reset_index(drop = True).copy(deep = True)

def get_experiment_config(sim_name: str, exp_num: int):
    sql = f"SELECT * FROM {DB_EXPERIMENT_CONFIG_TABLE} WHERE simulation_name = ? AND experiment_num = ?;"
    result = db_query_fetch(sql, (sim_name, exp_num))
    try:
        return json.loads(result[0]['config']), json.loads(result[0]['results'])
    except Exception as e:
        return None, None

def delete_experiment_data(sim_name: str, exp_num: int):
    sim_table = get_simulation_table_name(sim_name)
    sql = f"DELETE FROM {sim_table} WHERE experiment_num = {exp_num};"
    db_query_execute(sql, ())
    sql = f"DELETE FROM {DB_EXPERIMENT_CONFIG_TABLE} WHERE simulation_name = ? AND experiment_num = ?;"
    db_query_execute(sql, (sim_name, exp_num))
    return True
    
