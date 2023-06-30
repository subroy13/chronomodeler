from typing import List, Union, Dict
import time

from .base import BaseModel
from .enums import UserAuthLevel
from ..dbutils import db_query_execute, db_query_fetch


class User(BaseModel):

    _table = "users"
    _columns = [
        "userid", "username", "password_hash", "created_at", "updated_at", "authlevel"
    ]
    _identity = "userid"

    def __init__(
        self, 
        username: str,
        password_hash: str,
        created_at: int = None,
        updated_at: int = None,
        authlevel: UserAuthLevel = UserAuthLevel.PRIVATE,
        userid: int = None,
    ):
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at if created_at is not None else int(time.time())
        self.updated_at = updated_at if updated_at is not None else self.created_at
        self.userid = userid
        self.authlevel = authlevel.value if isinstance(authlevel, UserAuthLevel) else UserAuthLevel(authlevel)
        

    @classmethod
    def create_table(cls):
        sql = f"CREATE TABLE IF NOT EXISTS {cls._table} ( \
            userid integer primary key autoincrement, \
            username varchar(50) not null unique, \
            password_hash varchar(255) not null, \
            created_at integer not null, \
            updated_at integer not null, \
            authlevel integer not null default {UserAuthLevel.PRIVATE.value} \
        );"
        db_query_execute(sql, ())


    @classmethod
    def get_user_by_username(cls, username):
        sql = f"SELECT {','.join(cls._columns)} FROM {cls._table} WHERE username = ?;"
        res = db_query_fetch(sql, (username, ))
        if len(res) == 0:
            return None
        else:
            return cls(**res[0])