from typing import Optional, List, Dict, Literal, Union

from pydantic import BaseModel, Field, PositiveInt, ConfigDict, model_validator

from aomaker.session import BaseLogin

LOG_LEVEL = Literal["trace", "debug", "info", "success", "warning", "error", "critical"]
RUN_MODE = Literal["mp", "mt", "main"]
TestFilePathDict = Dict[Literal["path"], str]


class RunConfig(BaseModel):

    env: Optional[str] = None
    log_level: Optional[LOG_LEVEL] = "info"
    run_mode: Optional[RUN_MODE] = "main"
    task_args: Optional[Union[List[str], str, TestFilePathDict]] = None
    """
    用于并行模式的任务分发参数:
    - List[str]: 标记列表 (例如 ['-m mark1', '-m mark2'])
    - str: 测试套件目录路径
    - Dict[str, str]: 测试文件目录路径 (例如 {'path': 'tests/smoke'})
    对于单进程模式，此字段应为 None。
    """
    pytest_args: List[str] = Field(default_factory=list)
    login_obj: Optional[BaseLogin] = None
    report_enabled: bool = True
    processes: Optional[PositiveInt] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode='after')
    def check_parallel_args(self) -> 'RunConfig':
        if self.run_mode in ['mp', 'mt'] and self.task_args is None:
            raise ValueError(f"Run mode '{self.run_mode}' requires task_args for distribution.")
        return self

