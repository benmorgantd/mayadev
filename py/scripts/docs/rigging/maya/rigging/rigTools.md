# Module: rigTools

### Pipeline Intent
Provides utility functions for working with rigs in Maya. These utilities are used by the rig components and postops to perform common tasks on rigs, such as toggling skinning mode, matching ik to fk, etc.

### Technical Implementation
Exposed automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The `rigTools` module contains a set of utility functions for working with rigs in Maya. These utilities are designed to simplify common tasks that riggers perform, such as toggling skinning mode, matching ik to fk, and baking keyframes.

### Cross-Module Dependencies

* **Internal Framework Links:** 
    - `bmaya.maya.util.mathUtils`
    - `bmaya.core.constants`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `None`

#### Methods
None

---

### 🏷️ `FUNCTION` :: `toggleSkinMode`
**Signature:**
```python
def toggleSkinMode():
```
#### Description:
Toggles skinning mode on the currently built rig.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `sizeJoints`
**Signature:**
```python
def sizeJoints():
```
#### Description:
Sizes joints based on whether they are part of the bind set or not. If a joint is in the bind set, it sets the radius to 1; otherwise, it sets the draw style to 0.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `labelJoints`
**Signature:**
```python
def labelJoints():
```
#### Description:
Labels joints based on their side (left, right, or middle) and type.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `getModuleNode`
**Signature:**
```python
def getModuleNode(ctrl):
```
#### Description:
Gets the module node associated with a given control.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.

#### Returns:
The module node associated with the control.

---

### 🏷️ `FUNCTION` :: `getCharacterNode`
**Signature:**
```python
def getCharacterNode(ctrl):
```
#### Description:
Gets the character node associated with a given control and its module node.

#### Parameters:
- `ctrl`: The control to retrieve the character node for.

#### Returns:
The character node associated with the control and its module node.

---

### 🏷️ `FUNCTION` :: `resetControl`
**Signature:**
```python
def resetControl(ctrl):
```
#### Description:
Resets a control's attributes based on their default values.

#### Parameters:
- `ctrl`: The control to reset.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `resetModule`
**Signature:**
```python
def resetModule(mod):
```
#### Description:
Resets a module's attributes based on their default values and those of its components.

#### Parameters:
- `mod`: The module to reset.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `resetCharacter`
**Signature:**
```python
def resetCharacter(ctrl):
```
#### Description:
Resets a character's attributes based on their default values and those of its modules.

#### Parameters:
- `ctrl`: The control to reset the character for.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `selectModule`
**Signature:**
```python
def selectModule(ctrl):
```
#### Description:
Selects a module's components in the Maya hierarchy.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `keyAll`
**Signature:**
```python
def keyAll(ctrl):
```
#### Description:
Sets keyframes for a character's modules and their components based on their current state.

#### Parameters:
- `ctrl`: The control to retrieve the character node for.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `keyIk`
**Signature:**
```python
def keyIk(ctrl):
```
#### Description:
Sets keyframes for a character's ik components based on their current state.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `keyFk`
**Signature:**
```python
def keyFk(ctrl):
```
#### Description:
Sets keyframes for a character's fk components based on their current state.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `matchIkToFk`
**Signature:**
```python
def matchIkToFk(ctrl):
```
#### Description:
Matches a character's ik components to its fk components based on their current state.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `matchFkToIk`
**Signature:**
```python
def matchFkToIk(ctrl):
```
#### Description:
Matches a character's fk components to its ik components based on their current state.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `bakeFkToIk`
**Signature:**
```python
def bakeFkToIk(ctrl, bakeRange=None):
```
#### Description:
Bakes a character's fk components to its ik components based on their current state and a given time range.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.
- `bakeRange`: The time range to bake the keyframes for (default is the entire animation).

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `bakeIkToFk`
**Signature:**
```python
def bakeIkToFk(ctrl, bakeRange=None):
```
#### Description:
Bakes a character's ik components to its fk components based on their current state and a given time range.

#### Parameters:
- `ctrl`: The control to retrieve the module node for.
- `bakeRange`: The time range to bake the keyframes for (default is the entire animation).

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `_getFirstSelection`
**Signature:**
```python
def _getFirstSelection():
```
#### Description:
Gets the first selection in Maya.

#### Parameters:
- None

#### Returns:
The first selection in Maya.