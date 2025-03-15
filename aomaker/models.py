from typing import List, Text, Dict, Any, Union
from pydantic import BaseModel
from pydantic.types import constr


class DistStrategyYaml(BaseModel):
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
