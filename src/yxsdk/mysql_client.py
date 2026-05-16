import time
from datetime import datetime, date
from decimal import Decimal
import mysql.connector

class Row(dict):
    def __init__(self, data):
        super().__init__()
        for key,value in data:
            self[key] = value

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)
    def __setitem__(self, key, value):
        if isinstance(value, datetime):
            value = value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, date):
            value = value.strftime('%Y-%m-%d')
        elif isinstance(value, Decimal):
            # 将 Decimal 转换为 int 或 float
            if value % 1 == 0:  # 如果是整数
                value = int(value)
            else:  # 如果是小数
                value = float(value)
        super().__setitem__(key, value)

class MysqlClient:
    def __init__(self, host, port, user, password, database):
        self._db = None
        self._host = host
        self._port = port or 3306
        self._user = user
        self._password = password
        self._database = database
        self._max_idle_time = 7 * 3600
        self._last_use_time = time.time()
        try:
            self.reconnect()
        except Exception:
            raise Exception("Cannot connect to MySQL server")
    
    def __del__(self):
        self.close()

    def close(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None

    def reconnect(self):
        self.close()
        self._db = mysql.connector.connect(host=self._host, port=self._port, user=self._user, password=self._password, database=self._database, time_zone='+08:00')
        self._db.autocommit = True

    def _ensure_connected(self):
        if not self._db or (time.time() - self._last_use_time > self._max_idle_time):
            self.reconnect()
        self._last_use_time = time.time()

    def _cursor(self):
        self._ensure_connected()
        return self._db.cursor()
    
    def _execute(self, cursor, query, parameters, kwparameters):
        try:
            cursor.execute(query, kwparameters or parameters)
        except Exception:
            self.close()
            raise
    
    def query(self, query, *parameters, **kwparameters):
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            columns = [d[0] for d in cursor.description]
            return [Row(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def get(self, query, *parameters, **kwparameters):
        rows = self.query(query, *parameters, **kwparameters)
        if not rows:
            return None
        elif len(rows) > 1:
            raise Exception("Multiple rows returned for DBI.get() query")
        else:
            return rows[0]

    def execute_lastrowid(self, query, *parameters, **kwparameters):
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            return cursor.lastrowid
        finally:
            cursor.close()

    def execute_rowcount(self, query, *parameters, **kwparameters):
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            return cursor.rowcount
        finally:
            cursor.close()

    def execute(self, query, *parameters, **kwparameters):
        return self.execute_lastrowid(query, *parameters, **kwparameters)

    update = execute_rowcount
    insert = execute_lastrowid
    delete = execute_lastrowid

