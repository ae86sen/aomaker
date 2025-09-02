import sys
import attrs
from typing import Sequence, Union, Any, get_type_hints, get_origin, get_args
from typing import Dict as TDict, List as TList, Union as TUnion

from apischema import settings
from apischema.objects import ObjectField
from apischema.settings import ConstraintError


class CNErrorMessages:
    minimum: ConstraintError = "❌ 数值必须 ≥ {} (最小值限制)"
    maximum: ConstraintError = "❌ 数值必须 ≤ {} (最大值限制)"
    exclusive_minimum: ConstraintError = "❌ 数值必须 > {} (排他最小值)"
    exclusive_maximum: ConstraintError = "❌ 数值必须 < {} (排他最大值)"
    multiple_of: ConstraintError = "❌ 数值必须是 {} 的倍数"

    min_length: ConstraintError = "❌ 字符串长度不能小于 {}"
    max_length: ConstraintError = "❌ 字符串长度不能大于 {}"
    pattern: ConstraintError = "❌ 字符串格式不符合规则：{}"

    min_items: ConstraintError = "❌ 列表元素个数不能小于 {}"
    max_items: ConstraintError = "❌ 列表元素个数不能大于 {}"
    unique_items: ConstraintError = "❌ 列表中存在重复元素"

    min_properties: ConstraintError = "❌ 字段个数不能小于 {}"
    max_properties: ConstraintError = "❌ 字段个数不能大于 {}"

    one_of: ConstraintError = "❌ 输入必须是以下值之一：{}"

    unexpected_property: str = "❌ 出现了未定义的字段"
    missing_property: str = "❌ 缺少必填字段"


_prev_default_object_fields = settings.default_object_fields


def _normalize_type(tp: Any) -> Any:
    """
    将裸容器归一化，并递归处理 Union 等组合类型。
    - Dict -> Dict[str, Any]
    - List -> List[Any]
    """
    if tp is dict:
        return TDict[str, Any]
    if tp is list:
        return TList[Any]

    origin = get_origin(tp)
    args = get_args(tp)

    if origin is None:
        return tp

    # Union/Optional
    if origin is TUnion:
        norm_args = tuple(_normalize_type(a) for a in args)
        return TUnion[norm_args]  # type: ignore[index]

    # Dict 映射
    if origin in (dict, TDict):
        if len(args) != 2:
            return TDict[str, Any]
        key_t = _normalize_type(args[0])
        val_t = _normalize_type(args[1])
        return TDict[key_t, val_t]  # type: ignore[index]

    # List 序列
    if origin in (list, TList):
        if len(args) != 1:
            return TList[Any]
        item_t = _normalize_type(args[0])
        return TList[item_t]  # type: ignore[index]

    # todo: 其他容器后续按需扩展（Tuple/Set/Mapping...）
    return tp


def _attrs_fields(cls: type) -> Union[Sequence[ObjectField], None]:
    if hasattr(cls, "__attrs_attrs__"):
        # 解析注解为真实类型（兼容 from __future__ import annotations）
        try:
            module_globals = sys.modules[cls.__module__].__dict__
        except KeyError:
            module_globals = {}
        try:
            hints = get_type_hints(cls, globalns=module_globals, localns=dict(vars(cls)), include_extras=True)
        except Exception:
            hints = {}

        fields: list[ObjectField] = []
        for a in getattr(cls, "__attrs_attrs__"):
            raw_tp = hints.get(a.name, getattr(a, "type", Any))
            norm_tp = _normalize_type(raw_tp)
            fields.append(
                ObjectField(
                    a.name,
                    norm_tp,
                    required=a.default == attrs.NOTHING,
                    default=a.default,
                )
            )
        return fields
    else:
        # 非 attrs 类交回原默认处理
        return _prev_default_object_fields(cls)


def _set_default_object_fields():
    settings.default_object_fields = _attrs_fields
    settings.errors = CNErrorMessages