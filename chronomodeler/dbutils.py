import sqlite3
import streamlit as st

from .constants import SQLITE_DB


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


