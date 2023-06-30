from typing import List, Union, Dict
from abc import ABC, abstractmethod
from time import time

from ..dbutils import get_db_conn, db_query_execute, db_query_fetch

class BaseModel:
    """
        Base class for representing a row of different types of objects
        in a database table
    """

    _table: str = ""  # the name of the table
    _columns: List[str] = []  # the list of columns
    _searchcols: List[str] = []   # the list of searchable columns
    _identity: str = "id"   # the identity column
    _identity_insert: bool = False   # the column to insert
    created_at = None   # two default properties, always going to be added to track changes
    updated_at = None


    def to_dict(self) -> dict:
        return {
            col: getattr(self, col) for col in self._columns
        }
    
    
    @classmethod
    def create_table(cls):
        pass

    def insert(self):
        collist = [col for col in self._columns if self._identity_insert or col != self._identity]
        modeldict = self.to_dict()
        current_time = int(time())
        if "created_at" in modeldict:
            modeldict["created_at"] = current_time
            self.created_at = current_time
        if "updated_at" in modeldict:
            modeldict["updated_at"] = current_time
            self.updated_at = current_time
        params = [modeldict.get(col) for col in collist]
        sql = f"INSERT INTO {self._table}({ ','.join(collist) }) \
            VALUES ({ ','.join(['?' for col in collist]) }) \
            RETURNING {self._identity};"
        rows = db_query_fetch(sql, tuple(params))
        setattr(self, self._identity, rows[0][self._identity])

    def update(self):
        modeldict = self.to_dict()
        current_time = int(time())
        if "updated_at" in modeldict:
            modeldict["updated_at"] = current_time
            self.updated_at = current_time
        update_query_parts = []
        params = []
        for col in modeldict:
            val = modeldict.get(col)
            if val is not None and col != self._identity:
                params.append(val)
                update_query_parts.append(str(col) + " = ?")
        params.append(modeldict[self._identity])
        sql = f"UPDATE {self._table} SET {','.join(update_query_parts)} WHERE {self._identity} = ?;"
        db_query_execute(sql, tuple(params))

    @classmethod
    def get(cls, id):
        sql = f"SELECT {','.join(cls._columns)} FROM {cls._table} WHERE {cls._identity} = ?;"
        rows = db_query_fetch(sql, (id, ))
        if rows is None or len(rows) == 0:
            return None
        else:
            return cls(**rows[0])  # create a object of this class

    @classmethod
    def delete(cls, id):
        sql = f"DELETE FROM {cls._table} WHERE {cls._identity} = ?;"
        db_query_execute(sql, (id, ))

    
    @classmethod
    def list(cls, orderBy : Union[List[str], None] = None, limit: int = 0, offset: int = 0):
        collist = [col for col in cls._columns]
        if orderBy is None:
            orderBy = []
        orderByCol = orderBy if len(orderBy) > 0 else [cls._identity + " ASC"]
        sql = f"SELECT {','.join(collist)} \
            FROM {cls._table} \
            ORDER BY {','.join(orderByCol)} \
            {('LIMIT ' + str(limit) if limit > 0 else '')} \
            {('OFFSET ' + str(offset) if offset >= 0 else '' )};"
        rows = db_query_fetch(sql)
        if rows is None or len(rows) == 0:
            return []
        else:
            return [cls(**row) for row in rows]
        
    @classmethod
    def search(cls, query, userid):
        collist = [col for col in cls._columns]
        if 'userid' in collist:
            sql = f"SELECT {','.join(collist)} FROM {cls._table} \
            WHERE userid = ? AND ({'OR'.join([ (col + ' ILIKE ?') for col in cls._searchcols ])});"
            params = [userid] + (['%' + query + '%'] * len(cls._searchcols))
        else:
            sql = f"SELECT {','.join(collist)} FROM {cls._table} \
            WHERE ({'OR'.join([ (col + ' ILIKE ?') for col in cls._searchcols ])});"
            params =  ['%' + query + '%'] * len(cls._searchcols)
        rows = db_query_fetch(sql, tuple( params ) )
        if rows is None or len(rows) == 0:
            return []
        else:
            return [cls(**row) for row in rows]


