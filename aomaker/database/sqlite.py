import os
import sqlite3
import threading
from pathlib import Path

from aomaker._constants import DataBase


def get_db_path():
    current_dir = Path(os.getcwd()).resolve()
    while True:
        db_path = current_dir / 'database' / DataBase.DB_NAME
        if db_path.exists():
            return db_path
        if current_dir.parent == current_dir:
            raise FileNotFoundError(f"未找到数据库文件{DataBase.DB_NAME}")
        current_dir = current_dir.parent


DB_PATH = get_db_path()

lock = threading.RLock()


class SQLiteDB:

    def __init__(self, db_path=DB_PATH):
        """
        Connect to the sqlite database
        """
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def close(self):
        """
        Close the database connection
        """
        self.connection.close()

    def execute_sql(self, sql: str, params=()):
        if not isinstance(params, (tuple, list)):
            raise TypeError("SQL parameters must be a tuple or list")
        # with lock:
        self.cursor.execute(sql, params)
        self.connection.commit()

    def insert_data(self, table: str, data: dict):
        with lock:
            for key in data:
                data[key] = "'" + str(data[key]) + "'"
            key = ','.join(data.keys())
            value = ','.join(data.values())
            sql = """INSERT INTO {t} ({k}) VALUES ({v})""".format(t=table, k=key, v=value)
            self.execute_sql(sql)

    def upsert_data(self, table: str, data: dict, conflict_target: str):
        with lock:
            placeholders = ', '.join(['?'] * len(data))
            columns = ', '.join(data.keys())
            updates = ', '.join([f"{col}=excluded.{col}" for col in data.keys()])

            sql = f"""
            INSERT INTO {table} ({columns})
            VALUES ({placeholders})
            ON CONFLICT({conflict_target}) DO UPDATE SET
                {updates}
            """
            params = tuple(data.values())
            self.execute_sql(sql, params)

    def fetch_one(self, sql: str, params=()):
        """
        获取单行结果的快捷方法
        :return: 单行字典 或 None（无结果时）
        """
        results = self.query(sql, params)
        return results[0] if results else None

    def query(self, sql: str, params=()) -> list[dict]:
        with lock:
            self.cursor.execute(sql, params)
            columns = [col[0] for col in self.cursor.description] if self.cursor.description else []
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def select_data(self, table: str, select_field: str = "*", where: dict = None, is_fetch_all: bool = True):
        sql = f"SELECT {select_field} FROM {table}"
        params = ()

        if where:
            where_clause = ' AND '.join([f"{k} = ?" for k in where])
            sql += f" WHERE {where_clause}"
            params = tuple(where.values())

        if is_fetch_all:
            return self.query(sql, params)
        return self.fetch_one(sql, params)

    def update_data(self, table: str, data: dict, where: dict):
        with lock:
            set_clause = ', '.join([f"{k}=?" for k in data.keys()])
            where_clause = ' AND '.join([f"{k}=?" for k in where.keys()])

            sql = f"UPDATE {table} SET {set_clause}"
            if where:
                sql += f" WHERE {where_clause}"
            params = tuple(data.values()) + tuple(where.values())
            self.execute_sql(sql, params)

    def delete_data(self, table: str, where: dict = None):
        with lock:
            sql = f"DELETE FROM {table}"
            params = ()
            if where:
                where_clause = ' AND '.join([f"{k}=?" for k in where.keys()])
                sql += f" WHERE {where_clause}"
                params = tuple(where.values())

            self.execute_sql(sql, params)


if __name__ == '__main__':
    db = SQLiteDB()
