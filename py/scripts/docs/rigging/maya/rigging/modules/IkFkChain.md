# Module: IkFkChain

### Pipeline Intent
Enables the creation of IK/FK chains for character rigging, allowing animators to define complex joint hierarchies and blend between different poses.

### Technical Implementation
Imports necessary modules from `bmaya3` framework, including decorators and shape libraries. Inheriting from both `IkChain` and `FkChain`, this class combines the functionality of inverse kinematics (IK) and forward kinematics (FK) to create a single chain for character rigging.

### Overview
This module provides a comprehensive solution for creating IK/FK chains, allowing animators to define complex joint hierarchies and blend between different poses. By combining the functionalities of `IkChain` and `FkChain`, this class enables the creation of more realistic and nuanced character movements.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.base.decorators`, `bmaya3.rigging.shapes`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `IkFkChain`

**Purpose:** Combines the functionalities of IK and FK to create a single chain for character rigging.

*Inherits from:* `IkChain.IkChain`, `FkChain.FkChain`

#### Methods
- `__init__(self, ...)`: Initializes the IK/FK chain with given start and end joints, name, and other parameters.
- `build(self)`: Builds a single joint control on the given joint and sets up the FK/Ik setup.

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bindJoints = self.findHierarchyJoints(shortestDistance=True,
                                                   exclude=self.exclude)
        self.driveJoints = self.createDriveJoints(label='DRIVER',
                                                  constrain=True)

        self.buildFkIkSetup()

        self.components += self.ikComponents
        self.components += self.fkComponents

- `buildFkIkSetup(self, ...)`: Sets up the FK/Ik setup with drive joints and creates IK/FK components.

    def buildFkIkSetup(self, worldAimTarget=None, downAxis='X', upAxis='Y',
                       followWorld=True):
        # need to feed it our specific drive joints
        self.ikDriveJoints = self.createDriveJoints(label='IKDRIVER',
                                                    constrain=False)
        self.fkDriveJoints = self.createDriveJoints(label='FKDRIVER',
                                                    constrain=False)

        self.ikComponents = self.buildIkControls(self.ikDriveJoints,
                                                 worldAimTarget=worldAimTarget,
                                                 downAxis=downAxis,
                                                 upAxis=upAxis,
                                                 followWorld=followWorld)
        self.fkComponents = self.buildFkControls(self.fkDriveJoints)

        # add an attribute for blending
        cmds.addAttr(self.node, longName='FKIK', attributeType='float',
                     dv=self.fkikDefault,
                     min=0, max=1, keyable=True)

        self.blendReverse = self.blendChains(self.fkDriveJoints,
                                             self.ikDriveJoints,
                                             self.driveJoints,
                                             self.node + '.FKIK')

        # connect blend control to visibility
        cmds.connectAttr(self.blendReverse,
                         '{0}.v'.format(self.fkComponents[0].offsetGrp))
        cmds.connectAttr(self.node + '.FKIK',
                         '{0}.v'.format(self.ikComponents[0].offsetGrp))
        cmds.connectAttr(self.node + '.FKIK',
                         '{0}.v'.format(self.ikComponents[-1].offsetGrp))