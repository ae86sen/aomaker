import sqlite3
import threading
from typing import List, Dict
from pathlib import Path

from aomaker._constants import PROJECT_ROOT_FILE, DataBase


def find_project_root(start_path: Path) -> Path:
    current_path = start_path.resolve()
    while current_path != current_path.parent:
        if (current_path / PROJECT_ROOT_FILE).exists() or (current_path / "run.py").exists():
            return current_path
        current_path = current_path.parent
    raise FileNotFoundError(f"未找到项目根目录（缺少{PROJECT_ROOT_FILE}文件，可能不在aomaker项目中）")


def get_db_path() -> Path:
    project_root = find_project_root(Path.cwd())
    database_dir = project_root / DataBase.DB_DIR_NAME
    if not database_dir.exists():
        database_dir.mkdir(parents=True, exist_ok=True)
        print(f"创建 database 目录: {database_dir}")
    db_path = database_dir / DataBase.DB_NAME
    return db_path


lock = threading.RLock()


class SQLiteDB:

    def __init__(self, db_path=None):
        """
        Connect to the sqlite database
        """
        if db_path is None:
            db_path = get_db_path()
        self.connection = sqlite3.connect(db_path, check_same_thread=False, timeout=10)
        self.connection.execute("PRAGMA journal_mode=WAL")
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

    def query(self, sql: str, params=()) -> List[Dict]:
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
