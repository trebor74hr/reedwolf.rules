from enum import Enum
from typing import Callable, Any, List, _GenericAlias
from functools import reduce
from dataclasses import Field as DcField, is_dataclass
try:
    from pydantic import BaseModel as PydBaseModel
    from pydantic.fields import ModelField as PydModelField
    PydModelFieldType = PydModelField
except ImportError:
    PydBaseModel = None
    PydModelField = None
    PydModelFieldType = DcField # for typing

if PydBaseModel:
    from pydantic.main import ModelMetaclass as PydModelMetaclass # this must work

# ------------------------------------------------------------
# UNDEFINED
# ------------------------------------------------------------

class UndefinedType:

    instance:'UndefinedType'= None

    def __init__(self):
        if self.__class__.instance:
            raise ValueError("Undefined already instantiated, this is a singleton class")
        self.__class__.instance = self

    def __str__(self):
        return "UNDEFINED"
    def __bool__(self):
        return False 
    def __eq__(self, other):
        # if other is None: return False
        # same only to same or other UNDEFINED 
        if isinstance(other, self.__class__):
            return True
        return False 
    def __ne__(self, other):
        return not self.__eq__(other)
    __repr__ = __str__

UNDEFINED = UndefinedType()

# ------------------------------------------------------------
# Utility functions ...
# ------------------------------------------------------------

# nije ok ...
def composite_functions(*func:Callable[..., Any]) -> Callable[..., Any]:
    # inspired https://www.geeksforgeeks.org/function-composition-in-python/ 
    # TODO: see kwargs exmple at: https://mathieularose.com/function-composition-in-python
    """ accepts N number of function as an 
        argument and then compose them 
        returning single function that can be applied with """
    def compose(f, g):
        return lambda x : f(g(x))
              
    return reduce(compose, func, lambda x : x)

def is_pydantic(maybe_pydantic_class: Any) -> bool: 
    # TODO: ALT: maybe fails for partial functions: isinstance(maybe_pydantic_class) and issubclass(maybe_pydantic_class, PydBaseModel)
    return bool(PydBaseModel) and isinstance(maybe_pydantic_class, PydModelMetaclass)

def is_function(maybe_function: Any) -> bool: 
    # assert not isinstance(maybe_function, ValueExpression), maybe_function
    from .expressions import ValueExpression
    if isinstance(maybe_function, ValueExpression):
        return False
    # type() == type - to exclude list, dict etc.
    # type() == _GenericAlias to exclude typing.* e.g. List/Optional
    return callable(maybe_function) \
           and not type(maybe_function) in (type, _GenericAlias) \
           and not is_enum(maybe_function) \
           and not is_pydantic(maybe_function)

def is_enum(maybe_enum: Any) -> bool:
    return isinstance(maybe_enum, type) and issubclass(maybe_enum, Enum)


def get_available_vars_sample(var_name:str, var_list:List[str]):
    vars_avail = ', '.join([p for p in var_list if (p.startswith(var_name[:2] or var_name[:4] in p) and not p.startswith("_"))][:10])
    if not vars_avail:
        vars_avail = "{} ...".format(', '.join([p for p in var_list][:10]))
    elif len(vars_avail)<=3:
        vars_avail = "{} ... {}".format(', '.join([p for p in var_list][:10]), vars_avail)
    else: 
        vars_avail = "... {} ...".format(vars_avail)
    return vars_avail

def to_int(value, default=None):
    try:
        return int(value)
    except:
        return default

def snake_case_to_camel(name):
    out = []
    for var_name in name.split("."):
        class_name = []
        for bit in var_name.split("_"):
            bit = bit[0].upper()+bit[1:]
            class_name.append(bit)
        out.append("".join(class_name))
    return ".".join(out)

