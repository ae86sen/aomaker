from enum import Enum
from typing import List, Text, Dict, Any, Mapping, Union
from pydantic import BaseModel, Field, conlist, validator
from pydantic.types import constr

AssertField = conlist(Any, min_items=2, max_items=3)


class AssertFieldEnum(Text, Enum):
    eq = "eq"
    neq = "neq"
    gt = "gt"
    lt = "lt"
    ge = "ge"
    le = "le"
    contains = "contains"
    schema = "schema"


class RequestData(BaseModel):
    api_path: Text
    method: Text
    params: Dict = {}
    data: Dict = {}
    json_data: Dict = Field({}, alias='json')
    headers: Dict = {}


class ExtractField(BaseModel):
    var_name: Text
    expr: Text
    index: int = 0


class DependentApiField(BaseModel):
    module: Text
    api: Text
    extract: Text
    api_params: Dict = {}


class DependentParamsField(BaseModel):
    params: Text
    jsonpath: Text
    index: int = 0


class Steps(BaseModel):
    class_name: Text
    method_name: Text
    dependent_api: List[DependentApiField] = []
    dependent_params: List[DependentParamsField] = []
    request: RequestData
    assert_: List[Mapping[AssertFieldEnum, AssertField]] = Field([], alias='assert')
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
    config: Dict = {}
    steps: List[Steps]


class AomakerYaml(BaseModel):
    target: List
    marks: Dict[constr(min_length=1), Union[Dict[Text, List[Text]], List[Text]]]


class ExecuteAsyncJobCondition(BaseModel):
    expr: Text
    expected_value: Any


if __name__ == '__main__':
    def func(data: dict = None):
        m = ExecuteAsyncJobCondition(data)
        print(m)



    func(None)
