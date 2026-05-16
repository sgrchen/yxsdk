import time
import os
from datetime import datetime, date
from decimal import Decimal
import sqlite3

class Row(dict):
    def __init__(self, data):
        super().__init__()
        for key, value in data:
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

class SqliteClient:
    def __init__(self, database_path):
        self._db = None
        self._database_path = database_path
        self._max_idle_time = 7 * 3600
        self._last_use_time = time.time()
        
        # 确保数据库目录存在
        db_dir = os.path.dirname(database_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        try:
            self.reconnect()
        except Exception as e:
            raise Exception(f"Cannot connect to SQLite database: {e}")
    
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
        self._db = sqlite3.connect(self._database_path)
        # 启用外键约束
        self._db.execute("PRAGMA foreign_keys = ON")
        # 配置行工厂函数，让查询结果支持字典访问
        self._db.row_factory = sqlite3.Row

    def _ensure_connected(self):
        if not self._db or (time.time() - self._last_use_time > self._max_idle_time):
            self.reconnect()
        self._last_use_time = time.time()

    def _cursor(self):
        self._ensure_connected()
        return self._db.cursor()
    
    def _execute(self, cursor, query, parameters, kwparameters):
        try:
            if kwparameters:
                cursor.execute(query, kwparameters)
            else:
                cursor.execute(query, parameters)
        except Exception:
            self.close()
            raise
    
    def query(self, query, *parameters, **kwparameters):
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            if cursor.description:
                columns = [d[0] for d in cursor.description]
                return [Row(zip(columns, row)) for row in cursor.fetchall()]
            return []
        finally:
            cursor.close()
    
    def get(self, query, *parameters, **kwparameters):
        rows = self.query(query, *parameters, **kwparameters)
        if not rows:
            return None
        elif len(rows) > 1:
            raise Exception("Multiple rows returned for SqliteClient.get() query")
        else:
            return rows[0]

    def execute_lastrowid(self, query, *parameters, **kwparameters):
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            self._db.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    def execute_rowcount(self, query, *parameters, **kwparameters):
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            self._db.commit()
            return cursor.rowcount
        finally:
            cursor.close()

    def execute(self, query, *parameters, **kwparameters):
        return self.execute_lastrowid(query, *parameters, **kwparameters)

    def execute_script(self, script):
        """执行多条SQL语句"""
        self._ensure_connected()
        try:
            self._db.executescript(script)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def transaction(self):
        """返回事务上下文管理器"""
        return Transaction(self)

    update = execute_rowcount
    insert = execute_lastrowid
    delete = execute_rowcount


class Transaction:
    """SQLite事务上下文管理器"""
    
    def __init__(self, client):
        self.client = client
        
    def __enter__(self):
        self.client._ensure_connected()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.client._db.commit()
        else:
            self.client._db.rollback()