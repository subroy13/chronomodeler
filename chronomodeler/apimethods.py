# ============================================
#       Holds some of the API functionality that uses all models
# ============================================

import streamlit as st
import pandas as pd
import numpy as np

from chronomodeler.models import Simulation, Experiment, User
from chronomodeler.dbutils import get_db_conn, db_query_execute

def simulation_data_table_name(sim: Simulation, userid: int):
    user = User.get(userid)
    return f"{user.username}_{sim.sim_name}"

def insert_data_to_experiment(df: pd.DataFrame, expp: Experiment, sim: Simulation, userid: int):
    table_name = simulation_data_table_name(sim, userid)
    df['experiment_id'] = expp.expid
    if expp.initial:
        df.to_sql(table_name, get_db_conn(), if_exists="replace", index=False)
    else:
        # not initial experiment, should append
        sql = f"DELETE FROM {table_name} WHERE experiment_id = {expp.id}"
        db_query_execute(sql, ())

        # now append the data
        df.to_sql(table_name, get_db_conn(), if_exists="append", index=False)

    return True


def delete_simulation_data_table(sim: Simulation, userid: int):
    table_name = simulation_data_table_name(sim, userid)
    sql = f"DROP TABLE IF EXISTS {table_name};"
    db_query_execute(sql, ())


def get_simulation_data_initial(sim: Simulation, userid: int) -> pd.DataFrame:
    table_name = simulation_data_table_name(sim, userid)
    expp = sim.get_initial_experiment()
    sql = f"SELECT * FROM {table_name} WHERE experiment_id = {expp.expid};"
    df = pd.read_sql(sql, get_db_conn(), index_col=None, parse_dates=['Time'])
    return df