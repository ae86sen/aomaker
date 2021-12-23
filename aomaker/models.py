from typing import List, Text, Dict, Any, Mapping
from pydantic import BaseModel, Field, conlist, validator

AssertField = conlist(Any, min_items=2, max_items=3)


# JSON = List[Text, int, Any]


# class MethodEnumLower(Text, Enum):
#     get = "get"
#     post = "post"
#     put = "put"
#     delete = "delete"
#     head = "head"
#     options = "options"
#     patch = "patch"
#
#
# class MethodEnum(Text, Enum):
#     GET = "GET"
#     POST = "POST"
#     PUT = "PUT"
#     DELETE = "DELETE"
#     HEAD = "HEAD"
#     OPTIONS = "OPTIONS"
#     PATCH = "PATCH"


class RequestData(BaseModel):
    url_path: Text
    method: Text
    params: Dict = {}
    data: Dict = {}
    json_data: Dict = Field({}, alias='json')
    headers: Dict = {}


class ExtractField(BaseModel):
    var_name: Text
    expr: Text
    index: int = 0


class Steps(BaseModel):
    class_name: Text
    method_name: Text
    request: RequestData
    extract: List[ExtractField] = []
    assert_: List[Mapping[Text, AssertField]] = Field([], alias='assert')
    data_driven: Mapping[Text, List] = {}

    @validator('assert_')
    def check_assert_field(cls, v):
        assert_field_list = list(v[0].values())[0]
        if not isinstance(assert_field_list[0], str):
            raise ValueError('the first field in comparator must be str type!')
        if len(assert_field_list) == 3:
            assert isinstance(assert_field_list[1], int) is True, "jsonpath index must be int type!"
        return v


class YamlTestcase(BaseModel):
    testcase_class_name: Text
    testcase_name: Text
    description: Text = ''
    steps: List[Steps]

# data = {
#     'testcase_class_name': 123,
#     'testcase_name': 'add',
#     'description': '123',
#     'steps': [
#         {'class_name': 'cluster', 'method_name': 'add',
#          'request': {'url_path': '/api/', 'method': 'post', 'params': {'action': '123'}},
#          'extract': [{'var_name': 'asdasd', 'expr': '123'}],
#          'assert': [{'eq': ['asdsa',3]}],
#          'response': {'b': 123}}]
# }
# # assert_ = [{'eq': ['123', 1, 3]}]
# ass = YamlTestcase(**data)
# print(ass.dict(by_alias=True))
