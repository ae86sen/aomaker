# --coding:utf-8--
import json

from multiprocessing import current_process
from threading import current_thread

from aomaker.database.sqlite import SQLiteDB
from aomaker._constants import DataBase
from aomaker.log import logger

# __ALL__ = ["config", "schema", "stats", "cache","Config"]


class Config(SQLiteDB):
    def __init__(self,db_path=None):
        super(Config, self).__init__(db_path)
        self.table = DataBase.CONFIG_TABLE
        self.create_table()

    def create_table(self):
        sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table} (
            conf_name TEXT PRIMARY KEY,     
            value TEXT NOT NULL 
        );
        """
        self.execute_sql(sql)

    def set(self, conf_name: str, value):
        serialized_value = json.dumps(value)
        data = {"conf_name": conf_name, "value": serialized_value}

        self.upsert_data(table=self.table, data=data, conflict_target="conf_name")

    def get(self, conf_name: str):
        query_dict = {"conf_name": conf_name}
        result = self.select_data(self.table, where=query_dict, is_fetch_all=False)
        if result is None:
            return

        try:
            return json.loads(result['value'])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Data error for conf_name '{conf_name}': {str(e)}")
            return

    def get_all(self) -> dict:
        result = self.select_data(self.table)
        config_dict = {}
        for row in result:
            try:
                config_dict[row['conf_name']] = json.loads(row['value'])
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON for conf_name '{row['conf_name']}'")
                continue
        return config_dict

    def clear(self):
        self.delete_data(table=self.table)

    def del_by_condition(self, where: dict = None):
        """根据条件删除"""
        self.delete_data(table=self.table, where=where)


class Schema(SQLiteDB):
    def __init__(self,db_path=None):
        super(Schema, self).__init__(db_path)
        self.table = DataBase.SCHEMA_TABLE
        self.create_table()

    def create_table(self):
        sql = f""" CREATE TABLE IF NOT EXISTS {self.table} (
                schema_name TEXT PRIMARY KEY,
                schema_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );"""
        self.execute_sql(sql)

    def save_schema(self, schema_name: str, schema_: dict):
        data = {
            "schema_name": schema_name,
            "schema_json": json.dumps(schema_),
        }

        self.upsert_data(self.table, data=data, conflict_target="schema_name")

    def get_schema(self, schema_name: str):
        query_dict = {"schema_name": schema_name}
        result = self.select_data(self.table, "schema_json", query_dict, is_fetch_all=False)
        if result is None:
            return
        try:
            return json.loads(result['schema_json'])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Data error for schema_name '{schema_name}': {str(e)}")
            return

    def clear(self):
        self.delete_data(table=self.table)

    def del_by_condition(self, where: dict = None):
        self.delete_data(table=self.table, where=where)


class Cache(SQLiteDB):
    def __init__(self,db_path=None):
        super(Cache, self).__init__(db_path)
        self.table = DataBase.CACHE_TABLE
        self.create_table()

    def create_table(self):
        sql = f""" CREATE TABLE IF NOT EXISTS {self.table} (
                var_name TEXT,
                value TEXT,
                worker TEXT,
                UNIQUE(var_name, worker)
                );"""
        self.execute_sql(sql)

    @property
    def worker(self):
        run_mode = config.get("run_mode")
        worker = {
            "main": "MainProcess",
            "mt": current_thread().name,
            "mp": current_process().name
        }
        return worker[run_mode]

    def set(self, var_name: str, value):
        serialized_value = json.dumps(value)
        data = {"var_name": var_name, "value": serialized_value, "worker": self.worker}
        self.insert_data(table=self.table, data=data)

    def update(self, var_name: str, value):
        key_value = {"value": json.dumps(value)}
        condition = {"worker": self.worker, "var_name": var_name}
        self.update_data(self.table, key_value, where=condition)

    def upsert(self, var_name: str, value):
        key_value = {"worker": self.worker, "var_name": var_name, "value": json.dumps(value)}
        conflict_target = "var_name, worker"
        self.upsert_data(self.table, key_value, conflict_target)

    def get(self, var_name: str, select_field="value"):
        worker = self.worker
        sql = f"SELECT {select_field} FROM {self.table} WHERE var_name = ?"
        params = [var_name]

        if not (var_name == "headers" or var_name.startswith("_progress.")):
            sql += " AND worker = ?"
            params.append(worker)

        result = self.query(sql, tuple(params))

        if not result:
            return None

        try:
            res = result[0][select_field]
            return json.loads(res)
        except (KeyError, json.JSONDecodeError):
            return None

    def get_like(self, pattern: str):
        sql = f"""select distinct var_name from {self.table} where var_name like :pattern"""
        query_res = self.query(sql, (pattern,))
        keys = [row["var_name"] for row in query_res]
        return keys

    def clear(self):
        self.delete_data(table=self.table)

    def del_by_condition(self, where: dict = None):
        """根据条件删除"""
        self.delete_data(table=self.table, where=where)


class Stats(SQLiteDB):
    def __init__(self,db_path=None):
        super(Stats, self).__init__(db_path)
        self.table = DataBase.STATS_TABLE
        self.create_table()

    def create_table(self):
        sql = f"""CREATE TABLE IF NOT EXISTS {self.table} (package TEXT, api_name TEXT);"""
        self.execute_sql(sql)

    def set(self, *, package: str, api_name: str):
        self.insert_data(self.table, data={"package": package, "api_name": api_name})

    def get(self, conditions: dict = None):
        return self.select_data(table=self.table, where=conditions)

    def clear(self):
        self.delete_data(table=self.table)

    def del_by_condition(self, where: dict = None):
        self.delete_data(table=self.table, where=where)


cache = Cache()
config = Config()
schema = Schema()
stats = Stats()
