# Module: IkFkChain

### Pipeline Intent
Provides a framework for creating complex character rigs that blend between FK and IK controls.

### Technical Implementation
Combines the functionality of FkChain and IkChain classes to create a hybrid rigging system. Utilizes decorators from `bmaya.maya.rigging.base.decorators` to manage versioning utilities. Leverages shapes from `bmaya.maya.rigging.shapes.shapelib`.

### Overview
The IkFkChain module serves as the foundation for creating character rigs that seamlessly transition between FK (Forward Kinematics) and IK (Inverse Kinematics) control schemes.

### Cross-Module Dependencies
* **Internal Framework Links:** FkChain, IkChain, maya.cmds
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `IkFkChain`
**Purpose:** A hybrid rigging class that combines the functionality of FK and IK chains.

#### Methods
- `__init__(self, ...)`: Initializes the IkFkChain instance with various settings.
  - **Arguments:**
    - startJoint: Starting joint for the chain (default: None)
    - endJoint: Ending joint for the chain (default: None)
    - name: Name of the rigging component (default: 'IkFkChain1')
    - character: Character being rigged (default: None)
    - parent: Parent node for the rigging component (default: None)
    - mirror: Flag to indicate mirroring of the rig (default: False)
    - upVector: Up vector for the rigging component (default: [0, 2, 0])
    - exclude: List of joints to exclude from the chain (default: [])
    - side: Side of the character being rigged (default: 'L')
    - fkikDefault: Default value for the FK/IK blending attribute (default: 0)
    - alignWorld: Flag to align the rig with the world axis (default: True)

- `build(self)`: Builds a single joint control on the given joint and sets up the FK/IK blending.
  - **Returns:** None

- `buildFkIkSetup(self, ...)`: Sets up the IK and FK drive joints and controls for the character rig.

    * **Arguments:**
      - worldAimTarget: Target node to aim the IK chain at (default: None)
      - downAxis: Down axis for the IK chain (default: 'X')
      - upAxis: Up axis for the IK chain (default: 'Y')
      - followWorld: Flag to follow the world's rotation (default: True)

    * **Returns:** None

### Documentation Drift
None