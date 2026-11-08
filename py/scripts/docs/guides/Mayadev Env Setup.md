### Mayadev Environment Setup

## Environment Variable Setup in Maya.env
You have to give the following paths in `documents\maya\2026\Maya.env`
- `RIGGING_PROJECT_DIR` : The root of every game's projects, and the root asset ids are relative to (see [Asset Layout](Asset Layout.md))
- `MAYADEV_ROOT` : This is where your mayadev repo is installed
- `RIG_TEMPLATES_DIR` : This is the content folder where rig templates will be stored

Example:
```
RIGGING_PROJECT_DIR=C:\Users\morga\Documents\Art\Maya\rigs
MAYADEV_ROOT=C:\Users\morga\Documents\mayadev
RIG_TEMPLATES_DIR=C:\Users\morga\Documents\mayadev\py\scripts\bmaya3\maya\rigging\templates
```