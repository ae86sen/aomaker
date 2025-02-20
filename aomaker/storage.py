# --coding:utf-8--
import re
import sqlite3
import json
import hashlib

from jsonpath import jsonpath
from multiprocessing import current_process
from threading import current_thread

from aomaker.database.sqlite import SQLiteDB
from aomaker._constants import DataBase
from aomaker.exceptions import JsonPathExtractFailed
from aomaker.log import logger

__ALL__ = ["config", "schema", "stats", "cache"]


class Config(SQLiteDB):
    def __init__(self):
        super(Config, self).__init__()
        self.table = DataBase.CONFIG_TABLE

    def set(self, key: str, value):
        serialized_value = json.dumps(value)
        data = {"key": key, "value": serialized_value}
        try:
            self.insert_data(self.table, data=data)
        except sqlite3.IntegrityError as ie:
            logger.debug(f"config全局配置已加载=====>key: {key}, value: {value}")
            self.connection.commit()
            sql = "update {} set value=? where key=?".format(self.table)
            self.execute_sql(sql, (serialized_value, key))

    def get(self, key: str):
        sql = f"""select value from {self.table} where key=:key"""
        query_res = self.query_sql(sql, (key,))
        try:
            res = query_res[0][0]
        except IndexError:
            return None
        res = json.loads(res)

        return res

    def get_all(self) -> dict:
        """
        获取config表所有数据
        :return: {key:value,...}
        """
        all_data = self.select_data(self.table)
        dic = {}
        for m in all_data:
            dic[m[0]] = json.loads(m[1])
        return dic

    def clear(self):
        self.delete_data(table=self.table)

    def del_(self, where: dict = None):
        """根据条件删除"""
        self.delete_data(table=self.table, where=where)


class Schema(SQLiteDB):
    def __init__(self):
        super(Schema, self).__init__()
        self.table = DataBase.SCHEMA_TABLE
        self.create_table()

    def create_table(self):
        sql = f""" CREATE TABLE IF NOT EXISTS {self.table} (
                schema_key TEXT PRIMARY KEY,
                schema_json TEXT NOT NULL,
                original_route TEXT,
                method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        self.execute_sql(sql)

    def save_schema(self, endpoint, schema_: dict):
        key = SchemaKeyGenerator.get_schema_key(endpoint)
        data = {
            "schema_key": key,
            "schema_json": json.dumps(schema_),
            "original_route": endpoint.endpoint_config.route,
            "method": endpoint.endpoint_config.method.value
        }

        self.insert_data(self.table, data=data)

    def get_schema(self, endpoint) -> dict:
        key = SchemaKeyGenerator.get_schema_key(endpoint)
        sql = f"SELECT schema_json FROM {self.table} WHERE schema_key=:key"
        self.execute_sql(sql, (key,))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row else None

    def clear(self):
        self.delete_data(table=self.table)

    def del_(self, where: dict = None):
        """根据条件删除"""
        self.delete_data(table=self.table, where=where)

    def count(self):
        """数量统计"""
        sql = f"""select count(*) from {self.table}"""
        try:
            res = self.query_sql(sql)[0][0]
        except IndexError:
            logger.error("shema表数据统计失败！")
            res = None
        return res


class Cache(SQLiteDB):
    def __init__(self):
        super(Cache, self).__init__()
        self.table = DataBase.CACHE_TABLE

    @property
    def worker(self):
        run_mode = config.get("run_mode")
        worker = {
            "main": "MainProcess",
            "mt": current_thread().name,
            "mp": current_process().name
        }
        return worker[run_mode]

    def set(self, key: str, value, api_info=None, is_rewrite=False):
        worker = self.worker
        sql = f"""insert into {self.table} (var_name,response,worker) values (:key,:value,:worker)"""
        resp = self.get(key)
        if resp is not None:
            if is_rewrite is True:
                resp.update(value)
                sql = "update {} set response=? where var_name=? and worker=?".format(self.table)
                self.execute_sql(sql, (json.dumps(resp), key, worker))
            logger.debug(f"缓存插入重复数据, key:{key}，worker:{worker}，已被忽略！")
            return
        try:
            if api_info:
                sql = f"""insert into {self.table} (var_name,response,worker,api_info) values (:key,:value,:worker,:api_info)"""
                self.execute_sql(sql, (key, json.dumps(value), worker, json.dumps(api_info)))
            else:
                self.execute_sql(sql, (key, json.dumps(value), worker))
        except sqlite3.IntegrityError as e:
            raise e

    def update(self, key, value):
        key_value = {"response": json.dumps(value)}
        condition = {"worker": self.worker, "var_name": key}
        self.update_data(self.table, key_value, where=condition)
        logger.info(f"缓存数据更新完成, 表：{self.table},\n var_name: {key},\n response: {value},\n worker: {self.worker}")

    def get(self, key: str, select_field="response"):
        worker = self.worker
        if key == "headers" or key.startswith("_progress."):
            sql = f"""select {select_field} from {self.table} where var_name=:key"""
            query_res = self.query_sql(sql, (key,))
        else:
            sql = f"""select {select_field} from {self.table} where var_name=:key and worker=:worker"""
            query_res = self.query_sql(sql, (key, worker))
        try:
            res = query_res[0][0]
        except IndexError:
            return None
        res = json.loads(res)

        return res

    def get_by_jsonpath(self, key: str, jsonpath_expr, expr_index: int = 0):
        res = self.get(key)
        extract_var = jsonpath(res, jsonpath_expr)
        if extract_var is False:
            raise JsonPathExtractFailed(res, jsonpath_expr)
        extract_var = extract_var[expr_index]
        return extract_var

    def get_like(self, pattern: str):
        sql = f"""select distinct var_name from {self.table} where var_name like :pattern"""
        query_res = self.query_sql(sql, (pattern,))
        keys = [row[0] for row in query_res]
        return keys

    def clear(self):
        self.delete_data(table=self.table)

    def del_(self, where: dict = None):
        """根据条件删除"""
        self.delete_data(table=self.table, where=where)


class Stats(SQLiteDB):
    def __init__(self):
        super(Stats, self).__init__()
        self.table = DataBase.STATS_TABLE
        self.create_table()

    def create_table(self):
        sql = f"""CREATE TABLE IF NOT EXISTS {self.table} (package TEXT, api_name TEXT);"""
        self.execute_sql(sql)

    def set(self, *, package: str, api_name: str):
        self.insert_data(self.table, data={"package": package, "api_name": api_name})

    def get(self, conditions: dict = None):
        return self.select_data(table=self.table, where=conditions)


class SchemaKeyGenerator:
    @staticmethod
    def normalize_route(route: str) -> str:
        """将路由路径标准化（处理参数化路径差异）"""
        # 示例：/user/{id}/profile → /user/{}/profile
        return re.sub(r'\{\w+\}', '{}', route)

    @staticmethod
    def generate_route_hash(method: str, route: str) -> str:
        """生成路由指纹"""
        normalized = SchemaKeyGenerator.normalize_route(route)
        return hashlib.md5(f"{method}|{normalized}".encode()).hexdigest()[:8]

    @classmethod
    def get_schema_key(cls, endpoint) -> str:
        """生成最终使用的复合键"""
        if endpoint.endpoint_id:
            return endpoint.endpoint_id
        return f"{cls.generate_route_hash(endpoint.endpoint_config.method.value, endpoint.endpoint_config.route)}"


cache = Cache()
config = Config()
schema = Schema()
stats = Stats()
