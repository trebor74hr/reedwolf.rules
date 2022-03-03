from typing       import Callable, Optional, Dict, List, Any, Union
from dataclasses  import dataclass, field

from .utils import (
        UNDEFINED, 
        UndefinedType, 
        )
from .base        import (
        TypeHintField, 
        RulesHandlerFunction, 
        ComponentBase, 
        BoundModelBase
        )
from .expressions import ValueExpression


# ------------------------------------------------------------
# BoundModelHandler
# ------------------------------------------------------------

@dataclass
class BoundModelHandler(RulesHandlerFunction):
    pass

# ------------------------------------------------------------
# BoundModel
# ------------------------------------------------------------

@dataclass
class BoundModel(BoundModelBase):
    name            : str
    # label           : TransMessageType
    model           : Union[type, ValueExpression] = field(repr=False)
    contains        : Optional[List['BoundModel']] = field(repr=False, default_factory=list)
    # evaluated later
    owner           : Union[BoundModelBase, UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
    owner_name      : Union[str, UndefinedType] = field(init=False, default=UNDEFINED)
    type_hint_field : Optional[TypeHintField] = field(init=False, default=None, repr=False)

    def set_type_hint_field(self):
        assert self.type_hint_field is None
        # Done for compatibility.
        # NOTE: hard to fill automatically when ValueExpression, vexp is
        #       evaluated setup() what is a bit late in container.setup(). 
        assert not isinstance(self.model, ValueExpression), self
        self.type_hint_field = TypeHintField(py_type_hint=self.model, th_field=None, parent_object=None)

# ------------------------------------------------------------
# BoundModelWithHandlers
# ------------------------------------------------------------

@dataclass
class BoundModelWithHandlers(BoundModelBase):
    # TODO: razdvoji save/read/.../unique check 
    name         : str
    label        : str # TransMsg
    read_handler : BoundModelHandler
    save_handler : BoundModelHandler
    # --- evaluated later
    # filled from from type_hint_field
    model        : type = field(init=False, metadata={"skip_traverse": True}) 
    owner        : Union[BoundModelBase, UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
    owner_name   : Union[str, UndefinedType] = field(init=False, default=UNDEFINED)
    type_hint_field : Union[TypeHintField, UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
    # py_type_hint    : SimpleTypeHint = field(init=False, default=None, repr=False)

    def read(self, *args, **kwargs):
        return self.fn_read(*args, **kwargs)

    def save(self, *args, **kwargs):
        return self.fn_save(*args, **kwargs)

    def __post_init__(self):
        if not isinstance(self.read_handler, BoundModelHandler):
            raise RuleSetupValueError(owner=self, msg=f"read_handler={read_handler} should be instance of BoundModelHandler")
        if not isinstance(self.save_handler, BoundModelHandler):
            raise RuleSetupValueError(owner=self, msg=f"save_handler={save_handler} should be instance of BoundModelHandler")
        # if self.name=="device_types": import pdb;pdb.set_trace() 
        self.type_hint_field = TypeHintField.extract_function_return_type_hint_field(self.read_handler.function)
        self.model = self.type_hint_field.klass

        # TODO: verify:
        #   read() and save() method inject_parasm - params ok, param type matches vexp 
        #   model_param_name - found in save(), not found in read(), type in save() match
        #   any left params unset - without defaults?


