# --coding:utf-8--
import sqlite3
import json

from jsonpath import jsonpath
from multiprocessing import current_process
from threading import current_thread
from tabulate import tabulate

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


class Schema(SQLiteDB):
    def __init__(self):
        super(Schema, self).__init__()
        self.table = DataBase.SCHEMA_TABLE

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


class Stats(SQLiteDB):
    def __init__(self):
        super(Stats, self).__init__()
        self.table = DataBase.STATS_TABLE

    def set(self, *, package: str, module: str, api_class: str, api: str):
        sql = f"""insert into {self.table} (package,module,class,api) values (:package,:module,:api_class,:api)"""
        self.execute_sql(sql, (package, module, api_class, api))

    def get(self, conditions: dict = None):
        return self.select_data(table=self.table, where=conditions)
        # headers = ["Package", "Module", "Class", "API"]
        # print(f"Total APIs: {len(table_data)}")
        # return tabulate(table_data, headers=headers, tablefmt="grid")


def _get_worker():
    run_mode = config.get("run_mode")
    worker = {
        "main": "MainProcess",
        "mt": current_thread().name,
        "mp": current_process().name
    }
    return worker[run_mode]


cache = Cache()
config = Config()
schema = Schema()
stats = Stats()
