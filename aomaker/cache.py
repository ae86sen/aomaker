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


class Config(SQLiteDB):
    def __init__(self):
        super(Config, self).__init__()
        self.table = DataBase.CONFIG_TABLE

    def set(self, key: str, value):
        sql = f"""insert into {self.table}(key,value) values (:key,:value)"""
        value = json.dumps(value)
        try:
            self.execute_sql(sql, (key, value))
        except sqlite3.IntegrityError as ie:
            logger.debug(f"config全局配置已加载=====>key: {key}, value: {value}")
            self.connection.commit()
            sql = "update {} set value=? where key=?".format(self.table)
            self.execute_sql(sql, (value, key))

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
        """清空表"""
        sql = """delete from {}""".format(self.table)
        self.execute_sql(sql)

    def del_(self, where: dict = None):
        """根据条件删除"""
        sql = """delete from {}""".format(self.table)
        if where is not None:
            sql += ' where {};'.format(self.dict_to_str_and(where))
        self.execute_sql(sql)


class Schema(SQLiteDB):
    def __init__(self):
        super(Schema, self).__init__()
        self.table = DataBase.SCHEMA_TABLE
        self._create_table()

    def _create_table(self):
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
        sql = f"""INSERT INTO {self.table} (schema_key, schema_json, original_route, method)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(schema_key) DO UPDATE SET schema_json=excluded.schema_json
        """
        self.execute_sql(sql,(key, json.dumps(schema_), endpoint.endpoint_config.route, endpoint.endpoint_config.method.value))

    def get_schema(self, endpoint) -> dict:
        key = SchemaKeyGenerator.get_schema_key(endpoint)
        sql = f"SELECT schema_json FROM {self.table} WHERE schema_key="
        self.execute_sql(sql,(key,))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key: str, value):
        sql = f"""insert into {self.table} (api_name,schema) values (:key,:value)"""
        try:
            self.execute_sql(sql, (key, json.dumps(value)))
        except sqlite3.IntegrityError:
            logger.debug(f"Schema表插入重复数据，key: {key},已被忽略！")
            self.connection.commit()

    def get(self, key: str):
        sql = f"""select schema from {self.table} where api_name=:key"""
        query_res = self.query_sql(sql, (key,))
        try:
            res = query_res[0][0]
        except IndexError:
            return None
        res = json.loads(res)

        return res

    def clear(self):
        sql = """delete from {}""".format(self.table)
        self.execute_sql(sql)

    def del_(self, where: dict = None):
        """根据条件删除"""
        sql = """delete from {}""".format(self.table)
        if where is not None:
            sql += ' where {};'.format(self.dict_to_str_and(where))
        self.execute_sql(sql)

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

    def set(self, key: str, value, api_info=None):
        sql = f"""insert into {self.table} (var_name,response,worker) values (:key,:value,:worker)"""
        worker = _get_worker()
        if self.get(key) is not None:
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
        worker = _get_worker()
        condition = {"worker": worker, "var_name": key}
        self.update_data(self.table, key_value, where=condition)
        logger.info(f"缓存数据更新完成, 表：{self.table},\n var_name: {key},\n response: {value},\n worker: {worker}")

    def get(self, key: str, select_field="response"):
        worker = _get_worker()
        if key == "headers":
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

    def clear(self):
        sql = """delete from {}""".format(self.table)
        self.execute_sql(sql)

    def del_(self, where: dict = None):
        """根据条件删除"""
        sql = """delete from {}""".format(self.table)
        if where is not None:
            sql += ' where {};'.format(self.dict_to_str_and(where))
        self.execute_sql(sql)


def _get_worker():
    run_mode = config.get("run_mode")
    worker = {
        "main": "MainProcess",
        "mt": current_thread().name,
        "mp": current_process().name
    }
    return worker[run_mode]


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
