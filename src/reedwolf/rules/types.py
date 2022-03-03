from typing import Dict, List, Any, Union, Optional, Tuple
from decimal import Decimal
from datetime import date, datetime

# ------------------------------------------------------------
# SPECIAL DATATYPES
# ------------------------------------------------------------

# e.g. [(1,"test"), ("C2", "test2")]
STANDARD_TYPE_LIST      = (str, int, float, bool, Decimal, date, datetime)

StandardType            = Union[str, int, float, bool, Decimal, date, datetime]
TransMessageType        = str


# ChoiceValueType        = Tuple[StandardType, TransMessageType]


RuleDatatype            = Union[StandardType, List, Dict]

# NOTE: when custom type with ValueExpression alias are defined, then
#       get_type_hints falls into problems producing NameError-s
#         Object <class 'type'> / '<class 'reedwolf.rules.components.BooleanField'>' 
#         type hint is not possible/available: name 'OptionalBoolOrVExp' is not defined.
#
#   from .expressions import ValueExpression
#   BoolOrVExpType          = Union[bool, ValueExpression]
#   OptionalBoolOrVExpType  = Optional[BoolOrVExpType]
#   StandardTypeOrVExpType  = Union[StandardType, ValueExpression]
