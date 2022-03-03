from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from functools import partial
from dataclasses import dataclass, field, is_dataclass, Field as DcField
try:
    from pydantic.fields import ModelField as PydModelField
    PydModelFieldType = PydModelField
except ImportError:
    PydModelField = None
    PydModelFieldType = DcField # for typing

# fields as dc_fields
from enum import Enum

from .exceptions import (
        RuleSetupNameError, 
        RuleSetupNameNotFoundError, 
        RuleInternalError,
        )
from .utils import (
        is_pydantic, 
        is_function, 
        get_available_vars_sample,
        UNDEFINED, 
        UndefinedType, 
        )
from .base import (
        BoundVar, 
        TypeHintField,
        )
from .models import (
        BoundModelBase,
        )
from .expressions import (
        ValueExpression,
        )
from .namespaces import (
        Namespace, 
        ModelsNS, 
        ContextNS, 
        DataProvidersNS, 
        FieldsNS, 
        ThisNS, 
        UtilsNS, 
        GlobalNS,
        )

# ------------------------------------------------------------

class VariableTypeEnum(Enum):
    CALLABLE  = 1
    VEXP_FUNC = 2
    VEXP      = 3
    COMPONENT = 4
    OBJECT    = 5
    DC_FIELD  = 6
    PYD_FIELD = 7


@dataclass
class Variable:
    name:str
    # TODO: data can be also - check each: 
    #   - some dataproviding function
    #   - Utils function
    data:Union[TypeHintField, Callable[..., Any], ValueExpression, 'Component', type]
    namespace:Namespace
    # is_list:bool
    denied:bool=False
    deny_reason:str=""
    type: VariableTypeEnum = field(init=False)
    references: List[str] = field(init=False, default_factory=list, repr=False)
    bound_list: List[BoundVar] = field(init=False, default_factory=list, repr=False)

    def __post_init__(self):
        from .components import Component

        if not isinstance(self.name, str) or self.name in (None, UNDEFINED):
            raise RuleInternalError(owner=self, msg=f"Variable should have string name, got: {self.name}")

        if isinstance(self.data, TypeHintField):
            self.type = self.data.var_type
            self.data_supplier_name = f"{self.data.var_type}({self.data.klass})"
        elif callable(self.data):
            self.type = VariableTypeEnum.CALLABLE
            # not nice name
            self.data_supplier_name = f"{self.data.__name__}"
        elif isinstance(self.data, ValueExpression):
            if self.data.func_args:
                self.type = VariableTypeEnum.VEXP_FUNC
            else:
                self.type = VariableTypeEnum.VEXP
            self.data_supplier_name = f"{self.data!r}"
        elif isinstance(self.data, Component):
            self.type = VariableTypeEnum.COMPONENT
            self.data_supplier_name = f"{self.data.name}"
        else:
            # TODO: 3rd type callable Expression
            self.type = VariableTypeEnum.OBJECT
            self.data_supplier_name = f"{self.data.__class__.__name__}"

        self.full_name = f"{self.namespace._name}.{self.name}"

    def add_bound_var(self, bound_var:BoundVar):
        # for now just info field
        self.bound_list.append(bound_var)

    def add_reference(self, component_name:str):
        self.references.append(component_name)

    @property
    def refcount(self) -> int:
        return len(self.references)

    def isoptional(self):
        if isinstance(self.data, TypeHintField):
            out = self.data.is_optional
        # TODO: DataVar and others
        #   from .components import DataVar
        else: 
            out = False
        return out

    def islist(self):
        from .components import DataVar
        if isinstance(self.data, TypeHintField):
            out = self.data.is_list
        elif isinstance(self.data, DataVar):
            # TODO: DataVar to have TypeHintField too
            out = isinstance(self.data.datatype, list)
        else: 
            out = False
        return out

    def __str__(self):
        denied = ", DENIED" if self.denied else ""
        bound= (", BOUND={}".format(", ".join([f"{heap_name}->{ns._name}.{var_name}" for heap_name, ns, var_name in self.bound_list]))) if self.bound_list else ""
        return f"Variable({self.full_name} :{self.data_supplier_name}, rc={self.refcount}{bound}{denied})"

    def __repr__(self):
        return str(self)

# ------------------------------------------------------------

class VariablesHeap:

    def __init__(self, owner:'ContainerBase'):
        # self.variables : Dict[str, List[Variable]] = {}
        self.owner = owner
        self.name = owner.name
        self.variables_count:int = 0
        self.variables = { ns._name : {} for ns in [ModelsNS, ContextNS, DataProvidersNS, FieldsNS, UtilsNS, GlobalNS]}
        self.finished = False

    def __str__(self):
        counts = ", ".join([f"{k}={len(v)}" for k, v in self.variables.items() if v])
        # name={self.name}, 
        return f"VariablesHeap(owner={self.owner}, cnt={self.variables_count}, {counts})"

    def __repr__(self):
        return str(self)

    def __getattr__(self, attr_name:str):
        if attr_name in self.variables:
            return self.variables[attr_name]
        raise AttributeError(f"Unknown attribute '{attr_name}', available: {','.join(self.variables.keys())}")

    def is_empty(self):
        # return len(self.variables)==0
        return self.variables_count==0

    def add(self, variable:Variable, alt_var_name=None):
        assert not self.finished
        assert isinstance(variable, Variable), f"{type(variable)}->{variable}"
        var_name = alt_var_name if alt_var_name else variable.name
        if var_name in self.variables[variable.namespace._name]:
            raise RuleSetupNameError(owner=self, msg=f"Variable {variable} does not have unique name within NS {variable.namespace._name}, found: {self.variables[variable.namespace._name][var_name]}")
        self.variables[variable.namespace._name][var_name] = variable
        self.variables_count+=1

    # ------------------------------------------------------------

    def get_var(self, 
                namespace:Namespace, 
                var_name:str, 
                default:[None, UndefinedType]=UNDEFINED, 
                strict:bool=False 
                ) -> Union[Variable, None, UndefinedType]:
        if strict and var_name not in self.variables[namespace._name]:
            raise RuleSetupNameError(owner=self, msg=f"Variable not found {namespace}.{var_name}")
        assert var_name
        return self.variables[namespace._name].get(var_name, default)

    # ------------------------------------------------------------

    def get_var_by_bound_model(self, 
                               bound_model:BoundModelBase, 
                               default:[None, UndefinedType]=UNDEFINED,
                               strict:bool=False
                               ) -> Union[Variable, None, UndefinedType]:
        # allways in models
        var_name = bound_model.name
        assert var_name
        if strict and var_name not in self.variables[ModelsNS._name]:
            raise RuleSetupNameError(owner=self, msg=f"Variable not found {ModelsNS}.{var_name}")
        return self.variables[ModelsNS._name].get(var_name, default)

    # ------------------------------------------------------------

    def get_var_by_vexp(self, 
                        vexp:ValueExpression, 
                        default:[None, UndefinedType]=UNDEFINED,
                        strict:bool=False
                        ) -> Union[Variable, None, UndefinedType]:
        # similar logic in vexp.GetVariable()
        if vexp._var_name in (UNDEFINED, None): # or check vexp._status
            if strict:
                raise RuleSetupNameError(owner=self, msg=f"Variable's initialization did not finish successfully {vexp} -> {vexp}.{vexp._status}")
            return default
        var_name = vexp._var_name
        if not var_name:
            raise RuleInternalError(owner=self, msg=f"Variable name not set")
        if strict and var_name not in self.variables[vexp._namespace._name]:
            raise RuleSetupNameError(owner=self, msg=f"Variable not found {vexp._namespace._name}.{var_name}")
        return self.variables[vexp._namespace._name].get(var_name, default)

    # ------------------------------------------------------------

    def finish(self):
        if self.finished:
            raise RuleSetupError(owner=self, msg=f"Method finish() already called.")
        for ns, variables in self.variables.items():
            for vname, variable in variables.items():
                # do some basic validate
                if vname!=variable.name:
                    found = [var_name for heap_name, ns, var_name in variable.bound_list if vname==var_name]
                    if not found:
                        raise RuleInternalError(owner=self, msg=f"Variable name not the same as stored in heap {variable.name}!={vname} or bound list: {variable.bound_list}")

        self.finished = True

    # ------------------------------------------------------------

    # TODO: owner not used at all??

    # owner:"Component", 
    def getset_attribute_var(self, namespace:Namespace, var_name:str, parent_var:Variable) -> Variable:
        """ 
        Will create a new variable when missing, even in the case when the var
        is just "on the path" to final variable needed.
        """
        # can return ValueExpression / class member / object member
        # TODO: circ dep?
        from .components import DataVar

        if var_name.startswith("_"):
            raise RuleSetupNameError(owner=self, msg=f"Variable '{var_name}' is invalid, should not start with _")

        # if "eva_dts_readout_time_array" in var_name: import pdb;pdb.set_trace() 
        if parent_var is not None:

            if not isinstance(parent_var, Variable):
                raise RuleSetupNameError(owner=self, msg=f"Variable '{var_name}' -> parent_var={parent_var} :{type(parent_var)} is not Variable")

            if isinstance(parent_var.data, DataVar):
                inspect_object = parent_var.data.value
            elif isinstance(parent_var.data, BoundModelBase):
                inspect_object = parent_var.data.model
            else:
                inspect_object = parent_var.data

            type_hint_field = TypeHintField.extract_type_hint_field(var_name=var_name, inspect_object=inspect_object)

            # try to add variable with all needed infos
            assert parent_var.name!=var_name
            var_attribute_name = f"{parent_var.name}.{var_name}" 

            var = self.get_var(namespace, var_attribute_name)
            if not var:
                # missing - add it
                var = Variable(var_attribute_name, type_hint_field, namespace=namespace) # , is_list=False)
                self.add(var)
        else:
            if namespace==ContextNS:
                raise NotImplementedError("get_attribute::ContextNS - not implemented yet")
            elif namespace==ThisNS:
                raise NotImplementedError("get_attribute::ThisNS - not implemented yet")
            else:
                # global types - prefilled
                # current_owner.data.value.__annotations__
                # {'return': typing.List[domain.cloud.company.rules.CompanyVatNumbervalues]}
                if namespace._name not in self.variables:
                    raise RuleSetupNameError(owner=self, msg=f"Variable {var_name} namespace {namespace._name} is not valid. Valid namespace names are: {','.join(self.variables.keys())}")
                if var_name not in self.variables[namespace._name]:
                    vars_avail = get_available_vars_sample(var_name, self.variables[namespace._name].keys())
                    # if f"{namespace._name}.{var_name}"=="Models.company":
                    #     import pdb;pdb.set_trace() 
                    raise RuleSetupNameNotFoundError(owner=self, msg=f"Variable name {namespace._name}.{var_name} is not valid. Valid are: {vars_avail}")

                var = self.variables[namespace._name][var_name]

        return var

    # ------------------------------------------------------------

    # # OBSOLETE - replaced with vexp.GetVariable + vexp.Setup calls
    # # , var_name:Optional[str]
    # def get_vexp_type(self, vexp:ValueExpression) -> Tuple[type, bool]:
    #     """ returns type and if wrapped in List[] or not
    #     TODO: currently only This/ModelsNS uses this, e.g.:
    #             M.parent.attribute can be read - for ModelNS 
    #             supports only .parent.child or .child notation :(
    #     """
    #     # if not var_name: 
    #     #     var_name = vexp._name

    #     if len(vexp.Path)==2:
    #         var_name = vexp.Path[-2]._name
    #         var_attr = vexp.Path[-1]._name
    #     elif len(vexp.Path)==1:
    #         var_name = vexp.Path[-1]._name
    #         var_attr = None
    #     else:
    #         raise RuleSetupNameError(owner=self, item=vexp, msg=f"ValueExpression should have exactly 1 or 2 parts, e.g. M.person.adressses or M.persons, got: {vexp.Path}")

    #     variable = self.getset_attribute_var(vexp._namespace, var_name, owner=None, parent=None)

    #     if not variable:
    #         raise RuleSetupError(owner=self, item=vexp, msg=f"ValueExpression value {var} not found, valid are: TODO!")

    #     assert isinstance(variable, Variable)

    #     is_list = False
    #     if var_attr is None:
    #         var_type = variable.data
    #         # variable.type
    #     else:
    #         data = variable.data
    #         # TODO: use utils/base extract_ function instead
    #         if is_dataclass(data):
    #             fields = data.__dataclass_fields__
    #         elif is_pydantic(data):
    #             fields = data.__fields__
    #         else:
    #             raise RuleSetupNameError(owner=self, item=vexp, msg=f"Var {var_name} needs to be a @dataclass var, got: {type(data)}")

    #         # dc_fields()
    #         if var_attr not in fields:
    #             raise RuleSetupNameError(owner=self, item=vexp, msg=f"Variable {var_name} attribute {var_attr} not found. Valid are: TODO")

    #         # var_field = vexp.__dataclass_fields__[var_attr]
    #         var_type_hint = extract_py_type_hints(data, f"vexp->{vexp}:DC/PYD")
    #         var_type_hint = var_type_hint[var_attr]

    #         var_type_top = var_type_under = None

    #         if is_dataclass(var_type_hint) or is_pydantic(var_type_hint):
    #             var_type = var_type_hint
    #         else:
    #             var_type_top = getattr(var_type_hint, "__origin__", None)
    #             var_type_under = getattr(var_type_hint, "__args__", None)
    #             assert var_type_top
    #             # TODO: add Optional/List metainfo to vexp ...
    #             if var_type_top==list: # List
    #                 assert var_type_under and len(var_type_under)==1
    #                 var_type = var_type_under[0]
    #                 is_list = True
    #             elif var_type_top==Union: # Optional
    #                 assert var_type_under and len(var_type_under)==2
    #                 assert var_type_under[1]==type(None)
    #                 var_type = var_type_under[0]
    #             else:
    #                 assert not var_type_under
    #                 var_type = var_type_top

    #     # NOTE: can return this too:
    #     #   var_vexp, var_type_top, var_type_under
    #     return var_type, is_list

