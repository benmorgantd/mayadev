import os
import inspect
import sys
import importlib

dirname = os.path.dirname(os.path.abspath(__file__))

__all__ = [mod[0:-3] for mod in os.listdir(
    dirname) if mod.endswith('.py') and not mod.startswith('_')]

MODULE_CLASSES = {}
MODULE_ARGS = {}

for modType in __all__:

    # Python 3 compatible dynamic import
    module_path = f'bmaya.maya.rigging.modules.{modType}'
    importlib.import_module(module_path)

    # find the classes in that file
    modClasses = inspect.getmembers(sys.modules[module_path], inspect.isclass)

    ModClass = None

    for item in modClasses:
        # we're using the convention where the filename is the class name
        if item[0] == modType:
            ModClass = item[1]

    # Python 3 fix: Using getfullargspec instead of getargspec
    argspec = inspect.getfullargspec(ModClass.__init__)
    args = argspec.args
    # 'if this tuple has n elements, they correspond to the last n elements listed in args.'
    defaults = argspec.defaults or []

    numArgs = len(args)
    numDefaults = len(defaults)

    classArgs = {}

    startIndex = numArgs - numDefaults - 3
    j = 1

    for i in range(numDefaults - 1, startIndex, -1):
        if args[numArgs - j] not in ['name', 'modType', 'self', 'character']:
            classArgs[args[numArgs - j]] = defaults[i]
        j += 1

    MODULE_ARGS[modType] = classArgs
    MODULE_CLASSES[modType] = ModClass
