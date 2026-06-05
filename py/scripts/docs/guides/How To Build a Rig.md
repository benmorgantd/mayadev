### How To Create a Maya Rig

Note that you have to have the `RIGGING_PROJECT_DIR` environment variable set. This will determine where the root for rigs lives.

Code to build a simple rig from nothing:
```python 
from bmaya3.maya.asset.asset import Asset
from bmaya3.maya.rigging.base.rig import Rig

myRig = Rig('dev|prop|cube')
myRig.buildRig()
myRig.openFile(myRig.animRig.fullPath)
```

When you initialize a Rig object, it will create default files for everything. Its `build.json` will be the default `LayoutRig` found in the rig templates folder.