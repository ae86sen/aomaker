# --coding:utf-8--
import hashlib
import re
import json
from aomaker.database.sqlite import SQLiteDB

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


class SchemaManager(SQLiteDB):
    def __init__(self):
        super().__init__()
        self._create_table()
        self.table = "schema_test"

    def _create_table(self):
        cursor = self.cursor
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schemas (
                schema_key TEXT PRIMARY KEY,
                schema_json TEXT NOT NULL,
                original_route TEXT,
                method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.connection.commit()

    def save_schema(self, endpoint, schema: dict):
        key = SchemaKeyGenerator.get_schema_key(endpoint)
        cursor = self.cursor
        cursor.execute('''
            INSERT INTO schemas (schema_key, schema_json, original_route, method)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(schema_key) DO UPDATE SET schema_json=excluded.schema_json
        ''', (key, json.dumps(schema), endpoint.endpoint_config.route, endpoint.endpoint_config.method.value))
        self.connection.commit()

    def get_schema(self, endpoint) -> dict:
        key = SchemaKeyGenerator.get_schema_key(endpoint)
        cursor = self.cursor
        cursor.execute('SELECT schema_json FROM schemas WHERE schema_key=?', (key,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
