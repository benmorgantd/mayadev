### Mayadev Environment Setup

## Environment Variable Setup in Maya.env
You have to give the following paths in `documents\maya\2026\Maya.env`
- `RIGGING_PROJECT_DIR` : The root of every game's projects, and the root asset ids are relative to (see [Asset Layout](Asset Layout.md))
- `MAYADEV_ROOT` : This is where your mayadev repo is installed
- `RIG_TEMPLATES_DIR` : This is the content folder where rig templates will be stored
- `RIGMODULES_PLUGIN` (optional) : The `RigModules.mll` that startup loads. Defaults to the plugin name `RigModules`, which only works once the plugin is on `MAYA_PLUG_IN_PATH`. Point it at a copy of the build, not `cpp\x64\Release\RigModules.mll` itself: a loaded plugin locks the file, so the next build would fail.

Example:
```
RIGGING_PROJECT_DIR=C:\Users\morga\Documents\Art\Maya\rigs
MAYADEV_ROOT=C:\Users\morga\Documents\mayadev
RIG_TEMPLATES_DIR=C:\Users\morga\Documents\mayadev\py\scripts\bmaya3\maya\rigging\templates
RIGMODULES_PLUGIN=C:\Users\morga\Documents\maya\plug-ins\RigModules.mll
```

## RigModules menu
When startup loads RigModules, it adds a **RigModules** menu built from `toolsets/rigmodules_menu.json`. If the plugin doesn't load, startup logs a warning and skips the menu. The tools have no windows of their own: they act on the selection and report errors in the Script Editor.

| Tool | Select | Does |
|---|---|---|
| Print Joint Markup | joints | Prints each joint's markup JSON |
| Remove Joint Markup | joints | Removes their markup |
| Select All Controls | one rig root (`rigRootModule`) | Selects every control in the rig |
| Select Mirror Controls | controls | Selects the controls on the other side instead |
| Mirror Shapes Left to Right / Right to Left | one rig root | Mirrors control shapes from one side to the other |
| Save Control Shapes... / Load Control Shapes... | one rig root | Saves or loads a shape file chosen in a file dialog |

The scripts live in `toolsets/master_tool_registry.json` and call the RigModules commands directly. Their tests are in `tests/rigging/rigmodules_menu`.