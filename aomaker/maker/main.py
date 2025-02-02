# --coding:utf-8--
import json

from aomaker.maker.parser import OpenAPIParser
from aomaker.maker.generator import Generator

with open("../aicp-dev.json", 'r', encoding='utf-8') as f:
    doc = json.load(f)
parser = OpenAPIParser(doc)
api_groups = parser.parse()

generator = Generator(output_dir="demo")
generator.generate(api_groups)