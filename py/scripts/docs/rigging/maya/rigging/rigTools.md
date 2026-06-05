# Module: rigTools

### Pipeline Intent
Provides utility functions for working with rigs in Maya. These functions are used by the rig components and postops to perform common tasks on rigs, such as toggling skinning mode, matching IK to FK, etc.

### Technical Implementation
Exposes various functionalities using the standard library `json`, `time`, and `maya.cmds`/`OpenMaya`. Handles directory generation asynchronously when creating nested version tracks. Utilizes the `constants` module from `bmaya3.core.util` for spine up-axis definition.

### Overview
The `rigTools` module contains a set of utility functions that can be used to work with rigs in Maya. These functions are designed to be used by the rig components and postops to perform common tasks on rigs, such as toggling skinning mode, matching IK to FK, etc.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.core.util`, `maya.cmds`, `OpenMaya`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: None
No classes defined in this module.

#### Functions

---

### 🏷️ `FUNCTION` :: `toggleSkinMode`

**Signature:**
```python
def toggleSkinMode():
```
**Purpose:** Toggles skinning mode on the currently built rig.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `sizeJoints`

**Signature:**
```python
def sizeJoints():
```
**Purpose:** Sizes joints based on their type (hand or non-hand).

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `labelJoints`

**Signature:**
```python
def labelJoints():
```
**Purpose:** Labels joints with their side and type.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `getModuleNode`

**Signature:**
```python
def getModuleNode(ctrl):
```
**Purpose:** Gets the module node from a given control.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.

#### Returns
- Module node

---

### 🏷️ `FUNCTION` :: `getCharacterNode`

**Signature:**
```python
def getCharacterNode(ctrl):
```
**Purpose:** Gets the character node from a given control's module node.

#### Parameters:
* `ctrl`: Control to retrieve the character node for.

#### Returns
- Character node

---

### 🏷️ `FUNCTION` :: `getCharacterModules`

**Signature:**
```python
def getCharacterModules(characterNode):
```
**Purpose:** Gets the modules from a given character node.

#### Parameters:
* `characterNode`: Character node to retrieve the modules for.

#### Returns
- List of module nodes

---

### 🏷️ `FUNCTION` :: `resetControl`

**Signature:**
```python
def resetControl(ctrl):
```
**Purpose:** Resets the attributes of a given control to their default values.

#### Parameters:
* `ctrl`: Control to reset the attributes for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `resetModule`

**Signature:**
```python
def resetModule(mod):
```
**Purpose:** Resets the attributes of a given module and its components to their default values.

#### Parameters:
* `mod`: Module node to reset the attributes for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `resetCharacter`

**Signature:**
```python
def resetCharacter(ctrl):
```
**Purpose:** Resets the attributes of a given character and its modules to their default values.

#### Parameters:
* `ctrl`: Control to reset the attributes for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `selectModule`

**Signature:**
```python
def selectModule(ctrl):
```
**Purpose:** Selects all components of a given module node.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `keyAll`

**Signature:**
```python
def keyAll(ctrl):
```
**Purpose:** Sets keyframes on all keyable attributes of a given character and its modules.

#### Parameters:
* `ctrl`: Control to retrieve the character node for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `keyIk`

**Signature:**
```python
def keyIk(ctrl):
```
**Purpose:** Sets keyframes on all keyable attributes of a given IK component.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `keyFk`

**Signature:**
```python
def keyFk(ctrl):
```
**Purpose:** Sets keyframes on all keyable attributes of a given FK component.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `matchIkToFk`

**Signature:**
```python
def matchIkToFk(ctrl):
```
**Purpose:** Matches the position of IK controls to FK joints.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `matchFkToIk`

**Signature:**
```python
def matchFkToIk(ctrl):
```
**Purpose:** Matches the position of FK joints to IK controls.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `bakeFkToIk`

**Signature:**
```python
def bakeFkToIk(ctrl, bakeRange=None):
```
**Purpose:** Bakes FK controls to IK positions within a given time range.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.
* `bakeRange`: Optional, specifies the time range to bake (start and end frames).

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `bakeIkToFk`

**Signature:**
```python
def bakeIkToFk(ctrl, bakeRange=None):
```
**Purpose:** Bakes IK controls to FK positions within a given time range.

#### Parameters:
* `ctrl`: Control to retrieve the module node for.
* `bakeRange`: Optional, specifies the time range to bake (start and end frames).

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `_getFirstSelection`

**Signature:**
```python
def _getFirstSelection():
```
**Purpose:** Gets the first selection made in Maya.

#### Returns
* First selected control or None if no control is selected.

---

Documentation Drift:

* None