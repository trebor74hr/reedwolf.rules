# TODO: this module probably should be merged into expressions - since there is circular depencdency - see __getattr__
from .exceptions import RuleSetupNameError

# ------------------------------------------------------------
# Namespaces - classes and singletons
# ------------------------------------------------------------
# Namespaces are dummy objects/classes to enable different namespaces in
# ValueExpression declaration


class RubberObjectBase:
    """
    Just to mark objects that are (too) flexible
    all attributes are "existing" returning again objects that are same alike.
    """
    pass


class Namespace(RubberObjectBase):

    RESERVED_ATTR_NAMES = {"_name",}

    def __init__(self, name):
        self._name = name

    def __str__(self):
        return f"{self._name}"

    def __repr__(self):
        return f"NS[{self._name}]"

    def __getattr__(self, aname):
        if aname in self.RESERVED_ATTR_NAMES: # , "%r -> %s" % (self._node, aname):
            raise RuleSetupNameError(f"{self!r}: Namespace attribute {aname} is reserved, choose another name.")

        from .expressions import ValueExpression
        return ValueExpression(node=aname, namespace=self)

    # def get_field_definition(self, vexpr):
    #     # context = self.components
    #     assert hasattr(self, "components"), "Call setup() first"
    #     assert vexpr.is_top
    #     if   isinstance(vexpr.namespace, ContextNS):
    #         raise NotImplementedError()
    #         self.manage
    #     elif isinstance(vexpr.namespace, DataProviderNS):
    #         raise NotImplementedError()
    #         self.dataproviders
    #     elif isinstance(vexpr.namespace, FieldsNS):
    #         raise NotImplementedError()
    #         self.fields # is an dict with UNDEFINED values on start, filled on init() with model attr values 
    #     elif isinstance(vexpr.namespace, ThisNS):
    #         raise NotImplementedError()
    #         # this is within context of Control - e.g. Select.option
    #     elif isinstance(vexpr.namespace, UtilsNS):
    #         raise NotImplementedError()
    #         # this one should call generic functions
    #     else:
    #         raise RuleSetupError(f"Unknown type {vexpr.namespace}, expected some known namespace")

# Instances - should be used as singletons

# the only namespace declaration in this module
GlobalNS = Namespace("G")

# Context - Direct access to managed models underneath and global Rules objects like Validation/Section etc
ContextNS = Namespace("Context")

# managed models
ModelsNS = Namespace("Models")

# DataProviders/DP - DataVar - can be list, primitive type, object, Option etc. 
#   evaluated from functions or Expressions 
# TODO: DP. can have only list of DataVar(s) - naming is not the best
DataProvidersNS = Namespace("DataProviders")

# Field/F - of current rules setup - current version - manage(d) model
FieldsNS = Namespace("Fields")

# This - values from a current context, e.g. iteration of loop, option in select
ThisNS = Namespace("This")

# Utils - common functions 
UtilsNS = Namespace("Utils")

# aliases
G = GlobalNS
Ctx  = ContextNS
M = ModelsNS
DP = DataProvidersNS
F = FieldsNS
This = ThisNS
Utils = UtilsNS

# ALL_NS_OBJECTS = (ContextNS, DataProvidersNS, FieldsNS, ThisNS, UtilsNS, GlobalNS)

