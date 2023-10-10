# --coding:utf-8--
import pymysql

from aomaker.log import logger


class Mysql:
    def __init__(self, **kwargs):
        try:
            self.con = pymysql.connect(charset="utf8", **kwargs)
        except Exception as e:
            logger.error(f'数据库连接失败，连接参数：{kwargs}')
            raise e
        else:
            self.cur = self.con.cursor()

    def get_one(self, sql):
        """获取查询到的第一条数据"""
        self.con.commit()
        self.cur.execute(sql)
        return self.cur.fetchone()

    def get_all(self, sql):
        """获取sql语句查询到的所有数据"""
        self.con.commit()
        self.cur.execute(sql)
        return self.cur.fetchall()

    def count(self, sql):
        """获取sql语句查询到的数量"""
        self.con.commit()
        res = self.cur.execute(sql)
        return res

    def close(self):
        # 关闭游标对象
        self.cur.close()
        # 断开连接
        self.con.close()