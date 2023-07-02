from typing import List, Union, Dict
import time, json


from .base import BaseModel
from ..dbutils import db_query_execute

class Experiment(BaseModel):

    _table = "experiments"
    _columns = [
        "expid", "exp_name", "simid", "config", "results", "created_at", "updated_at"
    ]
    _identity = "expid"
    _searchcols = ["exp_name"]


    def __init__(
        self,
        simid: int,
        exp_name: str,
        config,
        results,
        initial: bool = False,
        created_at: int = None,
        updated_at: int = None,
        expid: int = None
    ):
        self.simid = simid
        self.exp_name = exp_name
        self.config = json.loads(config) if isinstance(config, str) else config
        self.results = json.loads(results) if isinstance(results, str) else results
        self.initial = initial if isinstance(initial, bool) else bool(initial)
        self.created_at = created_at if created_at is not None else int(time.time())
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self.expid = expid
        self.initial = initial

    @classmethod
    def create_table(cls):
        sql = f"CREATE TABLE IF NOT EXISTS {cls._table} ( \
            expid integer primary key autoincrement,    \
            simid integer not null,     \
            exp_name varchar not null,     \
            config text not null,   \
            results text not null,  \
            initial boolean not null default false, \
            created_at integer not null, \
            updated_at integer not null, \
            FOREIGN KEY(simid) REFERENCES simulations(simid) ON DELETE CASCADE   \
        );"
        db_query_execute(sql, ())

    def to_dict(self) -> dict:
        tmp = super().to_dict()        
        tmp['config'] = json.dumps(self.config)
        tmp['results'] = json.dumps(self.results)
        tmp['initial'] = 1 if self.initial else 0
        return tmp



