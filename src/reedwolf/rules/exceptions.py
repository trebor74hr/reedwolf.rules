from typing import Optional

# TODO: check https://snarky.ca/unravelling-from/ - how to convert/transform exception

# Base errors
class RuleError(Exception):
    # TODO: validate that every call is marked for translations, check in constructor or using mypy
    def __init__(self, msg:str, owner:Optional['ComponentBase'] = None, item: Optional['Item'] = None):
        self.msg, self.owner, self.item = msg, owner, item
        # maybe type(item)?
        self.full_msg = self._get_full_msg() + (f" (item={repr(item)[:50]})" if self.item else "")

    def _get_full_msg(self) -> str:
        return f"{self.owner.name}: {self.msg}" if self.owner and getattr(self.owner, "name", None) \
                        else (f"{str(self.owner)}: {self.msg}" if self.owner else self.msg) 

    def __str__(self):
        return f"{self.__class__.__name__} => {self.full_msg}"
    __repr__ = __str__

# ------------------------------------------------------------
# General and internal errors
# ------------------------------------------------------------
class RuleInternalError(RuleError):
    pass

class RuleNameNotFoundError(RuleError):
    pass

# ------------------------------------------------------------
# Rules setup (boot time) validation errors
# ------------------------------------------------------------
class RuleSetupError(RuleError):
    pass

class RuleSetupValueError(RuleSetupError):
    pass

class RuleSetupNameNotFoundError(RuleSetupError):
    pass

class RuleSetupNameError(RuleSetupError):
    pass

class RuleSetupTypeError(RuleSetupError):
    pass


# ------------------------------------------------------------
# Validations
# ------------------------------------------------------------

class RuleValidationError(RuleError):
    def __init__(self, msg:str, owner:'ComponentBase', item : Optional['Item'] = None):
        " owner is required "
        super().__init__(msg=msg, owner=owner, item=item)

class RuleValidationFieldError(RuleError):
    def __init__(self, msg:str, owner:'Field', item : Optional['Item'] = None):
        " owner must be field and is required "
        super().__init__(msg=msg, owner=owner, item=item)

class RuleValidationValueError(RuleValidationError):
    pass

class RuleValidationCardinalityError(RuleValidationError):
    pass

