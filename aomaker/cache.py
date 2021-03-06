# --coding:utf-8--
import sqlite3
import json

from jsonpath import jsonpath

from aomaker.database.sqlite import SQLiteDB
from aomaker._constants import DataBase
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
            logger.debug(f"数据库插入同key数据，value已更新为最新值：{ie}")
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
        all_data = self.select(self.table)
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
        except sqlite3.IntegrityError as ie:
            logger.debug(f"数据库插入重复数据，已被忽略：{ie}")
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

    def set(self, key: str, value):
        sql = f"""insert into {self.table} (var_name,response) values (:key,:value)"""
        try:
            self.execute_sql(sql, (key, json.dumps(value)))
        except sqlite3.IntegrityError as ie:
            logger.debug(f"数据库插入重复数据，已被忽略：{ie}")
            self.connection.commit()

    def get(self, key: str):
        sql = f"""select response from {self.table} where var_name=:key"""
        query_res = self.query_sql(sql, (key,))
        try:
            res = query_res[0][0]
        except IndexError:
            return None
        res = json.loads(res)

        return res

    def get_by_jsonpath(self, key: str, jsonpath_expr, expr_index: int = 0):
        res = self.get(key)
        try:
            extract_var = jsonpath(res, jsonpath_expr)[expr_index]
        except TypeError as te:
            logger.error(f'依赖数据提取失败，\n 数据源：{res}\n 提取表达式：{jsonpath_expr}\n 索引：{expr_index}')
            raise te
        return extract_var

    def clear(self):
        sql = """delete from {}""".format(self.table)
        self.execute_sql(sql)


cache = Cache()
config = Config()
schema = Schema()
