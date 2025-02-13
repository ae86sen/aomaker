# --coding:utf-8--
import json

from aomaker.maker.config import OpenAPIConfig
from aomaker.maker.parser import OpenAPIParser
from aomaker.maker.generator import Generator


config = OpenAPIConfig(backend_prefix="aicp",frontend_prefix="portal_api")
with open("../aicp-dev.json", 'r', encoding='utf-8') as f:
    doc = json.load(f)
parser = OpenAPIParser(doc,config=config)
api_groups = parser.parse()

generator = Generator(output_dir="demo",config=config)
generator.generate(api_groups)