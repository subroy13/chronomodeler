from typing import List, Union, Dict
import time

from .base import BaseModel
from .experiment import Experiment
from ..dbutils import db_query_execute, db_query_fetch

class Simulation(BaseModel):
    

    _table = "simulations"
    _columns = [
        "simid", "userid", "sim_name", "table_name", "created_at", "updated_at"
    ]
    _identity = "simid"
    _searchcols = ["sim_name"]


    def __init__(
        self,
        userid: int,
        sim_name: str,
        table_name: str = None,
        created_at: int = None,
        updated_at: int = None,
        simid: int = None
    ):
        self.userid = userid
        self.sim_name = sim_name
        self.created_at = created_at if created_at is not None else int(time.time())
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self.userid = userid
        self.table_name = table_name if table_name is not None else f"{userid}_{sim_name}"
        self.simid = simid


    @classmethod
    def create_table(cls):
        sql = f"CREATE TABLE IF NOT EXISTS {cls._table} ( \
            simid integer primary key autoincrement,    \
            sim_name varchar(256) not null, \
            userid int not null,    \
            table_name varchar(256) not null, \
            created_at integer not null, \
            updated_at integer not null, \
            FOREIGN KEY(userid) REFERENCES users(userid) ON DELETE CASCADE \
        );"
        db_query_execute(sql, ())

    @classmethod
    def count(cls, userid):
        sql = f"SELECT COUNT(1) AS totalcount FROM {cls._table} WHERE userid = ?;"
        res = db_query_fetch(sql, (userid, ))
        if res is None or len(res) == 0:
            return 0
        else:
            return int(res[0].get('totalcount', 0))

    def get_initial_experiment(self):
        sql = f"SELECT {','.join(Experiment._columns)} FROM {Experiment._table} \
            WHERE simid = {self.simid} AND initial = true;"
        rows = db_query_fetch(sql, ())
        if rows is None or len(rows) == 0:
            return None
        else:
            return Experiment(**rows[0])

    def get_experiment_count(self):
        sql = f"SELECT draft, COUNT(1) AS totalcount FROM {Experiment._table} WHERE simid = {self.simid} AND initial = false GROUP BY draft;"
        res = db_query_fetch(sql, ())
        if res is None or len(res) == 0:
            return { 'draft': 0, 'final': 0 }
        else:
            return { 
                'draft': int([row['totalcount'] for row in res if row['draft']][0]), 
                'final': int([row['totalcount'] for row in res if not row['draft']][0])
            }
