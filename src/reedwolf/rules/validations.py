from typing import List, Optional, Union
from dataclasses import dataclass, field

from .exceptions import (
        RuleSetupError, 
        RuleValidationCardinalityError, 
        RuleSetupTypeError,
        )
from .utils import (
        to_int,
        UNDEFINED, 
        UndefinedType,
        )
from .base import (
        SetOwnerMixin,
        )

class ChildrenValidation(SetOwnerMixin):
    def is_finished(self):
        return bool(self.name)


class CardinalityValidation(ChildrenValidation): # count

    def __post_init__(self):
        if self.__class__==CardinalityValidation:
            raise RuleSetupError(owner=self, msg=f"Use subclasses of CardinalityValidation")

    def validate_setup(self):
        """
        if not ok, 
            raises RuleSetupTypeError
        """
        raise NotImplementedError("abstract method")

    def validate(self, items_count:bool, raise_err:bool=True) -> bool:
        """
        takes nr. of items and validates
        if ok, returns True
        if not ok, 
            if raise_err -> raises RuleValidationCardinalityError
            else -> return false
        """
        raise NotImplementedError("abstract method")

    def _validate_setup_common(self, allow_none:Optional[bool]=None) -> 'Variable':
        model_var = self.owner.get_bound_model_var()
        if allow_none is not None:
            if allow_none and not model_var.isoptional():
                raise RuleSetupTypeError(owner=self, msg=f"Type hint is not Optional and cardinality allows None. Add Optional or set .allow_none=False/min=1+")
            if not allow_none and model_var.isoptional():
                raise RuleSetupTypeError(owner=self, msg=f"Type hint is Optional and cardinality does not allow None. Remove Optional or set .allow_none=True/min=0")
        return model_var

# ------------------------------------------------------------

class Cardinality: # namespace holder

    @dataclass
    class Single(CardinalityValidation):
        name            : str
        allow_none      : bool = True

        owner           : Union['ContainerBase', UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
        owner_name      : Union[str, UndefinedType] = field(init=False, default=UNDEFINED)

        def validate_setup(self):
            model_var = self._validate_setup_common(self.allow_none)
            if model_var.islist():
                raise RuleSetupTypeError(owner=self, msg=f"Type hint is List and should be single instance. Change to Range/Multi or remove type hint List[]")

        def validate(self, items_count:int, raise_err:bool=True):
            if items_count==0 and not self.allow_none:
                if raise_err: 
                    raise RuleValidationCardinalityError(owner=self, msg=f"Expected exactly one item, got none.")
                return False
            if items_count!=1:
                if raise_err: 
                    raise RuleValidationCardinalityError(owner=self, msg=f"Expected exactly one item, got {items_count}.")
                return False
            return True

    @dataclass
    class Range(CardinalityValidation):
        """ 
            at least one (min or max) arg is required
            min=None -> any number (<= max)
            max=None -> any number (>= min)
            min=0    -> same as allow_none in other validations

        """
        name            : str
        min             : Optional[int] = None
        max             : Optional[int] = None

        owner           : Union['ContainerBase', UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
        owner_name      : Union[str, UndefinedType] = field(init=False, default=UNDEFINED)

        def __post_init__(self):
            if self.min is None and self.max is None:
                raise RuleSetupError(owner=self, msg=f"Please provide min and/or max")
            if self.min is not None and (to_int(self.min)==None or to_int(self.min)<0):
                raise RuleSetupError(owner=self, msg=f"Please provide integer min >=0 ")
            if self.max is not None and (to_int(self.max)==None or to_int(self.max)<0):
                raise RuleSetupError(owner=self, msg=f"Please provide integer max >=0 ")
            if self.min is not None and self.max is not None and self.max<self.min:
                raise RuleSetupError(owner=self, msg=f"Please provide min <= max")
            if self.max is not None and self.max==1:
                raise RuleSetupError(owner=self, msg=f"Please provide max>1 or use Single.")

        def validate_setup(self):
            model_var = self._validate_setup_common(allow_none=(self.min==0))
            if not model_var.islist():
                raise RuleSetupTypeError(owner=self, msg=f"Type hint is not List and should be. Change to Single or add List[] type hint ")

        def validate(self, items_count:int, raise_err:bool=True):
            if self.min and items_count < self.min:
                if raise_err: 
                    raise RuleValidationCardinalityError(owner=self, msg=f"Expected at least {self.min} item(s), got {items_count}.")
                return False
            if self.max and items_count < self.max:
                if raise_err: 
                    raise RuleValidationCardinalityError(owner=self, msg=f"Expected at most {self.max} items, got {items_count}.")
                return False
            return True

    @dataclass
    class Multi(CardinalityValidation):
        " [0,1]:N "
        name            : str
        allow_none      : bool = True

        owner           : Union['ContainerBase', UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
        owner_name      : Union[str, UndefinedType] = field(init=False, default=UNDEFINED)

        def validate_setup(self):
            model_var = self._validate_setup_common(self.allow_none)
            if not model_var.islist():
                raise RuleSetupTypeError(owner=self, msg=f"Type hint is not a List and should be. Change to Single or add List[] type hint")

        def validate(self, items_count:int, raise_err:bool=True):
            if items_count==0 and not self.allow_none:
                if raise_err: 
                    raise RuleValidationCardinalityError(owner=self, msg=f"Expected at least one item, got none.")
                return False
            return True


# ------------------------------------------------------------
# other validations
# ------------------------------------------------------------
class UniqueValidation(ChildrenValidation):

    def __post_init__(self):
        if self.__class__==UniqueValidation:
            raise RuleSetupError(owner=self, msg=f" Use subclasses of UniqueValidation")

    # def set_owner(self, owner):
    #     super().set_owner(owner)
    #     if not self.name:
    #         self.name = f"{self.owner.name}__{self.__class__.__name__.lower()}"

class Unique: # namespace holder

    @dataclass
    class Global(UniqueValidation):
        " globally - e.g. within table "
        name            : str
        fields          : List[str] # TODO: better field specification or vexpr?
        ignore_none     : bool = True

        owner           : Union['ContainerBase', UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
        owner_name      : Union[str, UndefinedType] = field(init=False, default=UNDEFINED)

    @dataclass
    class Children(UniqueValidation):
        " within extension records "
        name            : str
        fields          : List[str] # TODO: better field specification or vexpr?
        ignore_none     : bool = True

        owner           : Union['ContainerBase', UndefinedType] = field(init=False, default=UNDEFINED, repr=False)
        owner_name      : Union[str, UndefinedType] = field(init=False, default=UNDEFINED)


# ALT: names for ChildrenValidation
#   class IterationValidation:
#   # db terminology: scalar custom functions, table value custom functions, aggregate custom functions
#   class AggregateValidation: 
#   class ExtensionValidation:
#   class ItemsValidation:
#   class MultipleItemsValidation:
#   class ContainerItemsValidation:
