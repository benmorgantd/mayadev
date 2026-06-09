### How To Create a Maya Rig

Note that you have to have the `RIGGING_PROJECT_DIR` environment variable set. This will determine where the root for rigs lives.

Code to build a simple rig from nothing:
```python 
from bmaya.maya.asset import asset
from bmaya.maya.rigging.base import rig

my_rig = rig.Rig('dev|prop|cube')
my_rig.build_rig()
my_rig.open_file(myRig.animRig.full_path)
```

When you initialize a Rig object, it will create default files for everything. Its `build.json` will be the default `LayoutRig` found in the rig templates folder.