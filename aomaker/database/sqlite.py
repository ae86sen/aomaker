import os
import sqlite3
import threading

from aomaker._constants import DataBase
from aomaker.path import DB_DIR

DB_PATH = os.path.join(DB_DIR, DataBase.DB_NAME)

lock = threading.RLock()


class SQLiteDB:

    def __init__(self, db_path=DB_PATH):
        """
        Connect to the sqlite database
        """
        # check_same_thread=False
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def close(self):
        """
        Close the database connection
        """
        self.connection.close()

    def execute_sql(self, sql: str, *args, **kwargs):
        """
        Execute SQL
        """
        with lock:
            self.cursor.execute(sql, *args, **kwargs)
            self.connection.commit()

    def insert_data(self, table: str, data: dict):
        """
        insert sql statement
        """
        for key in data:
            data[key] = "'" + str(data[key]) + "'"
        key = ','.join(data.keys())
        value = ','.join(data.values())
        sql = """INSERT INTO {t} ({k}) VALUES ({v})""".format(t=table, k=key, v=value)
        self.execute_sql(sql)

    def query_sql(self, sql: str, *args, **kwargs):
        """
        Query SQL
        return: query data
        """
        data_list = []
        with lock:
            rows = self.cursor.execute(sql, *args, **kwargs)
            for row in rows:
                data_list.append(row)
            return data_list

    def select_data(self, table: str, where: dict = None):
        """
        select sql statement
        """
        sql = """select * from {}""".format(table)
        if where is not None:
            sql += 'where {};'.format(self.dict_to_str_and(where))
        return self.query_sql(sql)

    def update_data(self, table: str, data: dict, where: dict):
        """
        update sql statement
        """
        sql = """update {} set """.format(table)
        sql += self.dict_to_str(data)
        if where:
            sql += ' where {};'.format(self.dict_to_str_and(where))
        self.execute_sql(sql)

    def delete_data(self, table: str, where: dict = None):
        """
        delete table data
        """
        sql = """delete from {}""".format(table)
        if where is not None:
            sql += ' where {};'.format(self.dict_to_str_and(where))
        self.execute_sql(sql)

    def init_table(self, table_data: dict):
        """
        init table data
        """
        for table, data_list in table_data.items():
            self.delete_data(table)
            for data in data_list:
                self.insert_data(table, data)
        self.close()

    @staticmethod
    def dict_to_str(data: dict) -> str:
        """
        dict to set str
        """
        tmp_list = []
        for key, value in data.items():
            if value is None:
                tmp = "{k}={v}".format(k=key, v='null')
            elif isinstance(value, int):
                tmp = "{k}={v}".format(k=key, v=str(value))
            else:
                tmp = "{k}='{v}'".format(k=key, v=value)
            tmp_list.append(tmp)
        return ','.join(tmp_list)

    @staticmethod
    def dict_to_str_and(conditions: dict) -> str:
        """
        dict to where and str
        """
        tmp_list = []
        for key, value in conditions.items():
            if value is None:
                tmp = "{k}={v}".format(k=key, v='null')
            elif isinstance(value, int):
                tmp = "{k}={v}".format(k=key, v=str(value))
            else:
                tmp = "{k}='{v}'".format(k=key, v=value)
            tmp_list.append(tmp)
        return ' and '.join(tmp_list)


if __name__ == '__main__':
    db = SQLiteDB()
