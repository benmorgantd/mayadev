import os
import inspect
import sys

dirname = os.path.dirname(os.path.abspath(__file__))

__all__ = [mod[0:-3] for mod in os.listdir(
          dirname) if mod.endswith('.py') and mod != '__init__.py']

_MODULE_CLASSES = {}
_MODULE_ARGS = {}


for modType in __all__:

    exec('import bm.maya.Osiris.rigMods.' + modType)

    # find the classes in that file
    modClasses = inspect.getmembers(sys.modules['bm.maya.Osiris.rigMods.' + modType], inspect.isclass)

    ModClass = None

    for item in modClasses:
        # we're using the convention where the filename is the class name
        if item[0] == modType:
            ModClass = item[1]

    argspec = inspect.getargspec(ModClass.__init__)
    args = argspec.args
    # 'if this tuple has n elements, they correspond to the last n elements listed in args.'
    defaults = argspec.defaults

    numArgs = len(args)
    numDefaults = len(defaults)

    classArgs = {}

    startIndex = numArgs - numDefaults - 3
    j = 1

    for i in range(numDefaults - 1, startIndex, -1):
        print args[numArgs - j], defaults[i]
        if args[numArgs - j] not in ['name', 'modType', 'self', 'character']:
            classArgs[args[numArgs - j]] = defaults[i]
        j += 1

    print classArgs

    _MODULE_ARGS[modType] = classArgs
    _MODULE_CLASSES[modType] = ModClass
