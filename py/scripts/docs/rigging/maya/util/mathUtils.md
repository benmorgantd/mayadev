# Module: mathUtils


### Pipeline Intent
Provides utility functions for working with math in maya. These are used by various components to perform common tasks that involve math, such as finding the pole vector position for an ik handle, etc.


### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
mathUtils provides a set of utility functions for working with math in maya. This includes finding the pole vector position for an ik handle, setting up ik twist, fitting curves to points, getting matrices along curves, matching transforms, and more.


### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `None`
**Purpose:** None  
*Inherits from:* None

#### Methods
- N/A


### 🏷️ `FUNCTION` :: `findPoleVector`

**Signature:**
```python
def findPoleVector(joints, scaleFactor=1):
```
#### Arguments
- joints (list): A list of joint names.
- scaleFactor (float): The scale factor for the pole vector.

#### Returns
- A tuple containing the pole vector location in world space.


### 🏷️ `FUNCTION` :: `setupIkTwist`

**Signature:**
```python
def setupIkTwist(twistJoint=None, ikStartJoint=None, ikHandleParent=None, twistJointParent=None, name=None):
```
#### Arguments
- twistJoint (str): The joint to twist.
- ikStartJoint (str): The start joint of the ik chain.
- ikHandleParent (str): The parent joint of the ik handle.
- twistJointParent (str): The parent joint of the twist joint.
- name (str): The name for the ik twist.

#### Returns
- A tuple containing the ik twist start and group.


### 🏷️ `FUNCTION` :: `setupQuatTwist`

**Signature:**
```python
def setupQuatTwist(obj=None, twistAxis="X"):
```
#### Arguments
- obj (str): The object to twist.
- twistAxis (str): The axis of the twist.

#### Returns
- A node that performs the quaternion twist.


### 🏷️ `FUNCTION` :: `fitCurveToPoints`

**Signature:**
```python
def fitCurveToPoints(points, name='fitCurve'):
```
#### Arguments
- points (list): A list of points to fit.
- name (str): The name for the curve.

#### Returns
- The fitted curve.


### 🏷️ `FUNCTION` :: `getMatrixAlongCurve`

**Signature:**
```python
def getMatrixAlongCurve(curve, parameter, downAxis='X'):
```
#### Arguments
- curve (str): The curve to get the matrix for.
- parameter (float): The parameter along the curve.
- downAxis (str): The axis of the down vector.

#### Returns
- A matrix representing the position and orientation at the given parameter.


### 🏷️ `FUNCTION` :: `matchTransforms`

**Signature:**
```python
def matchTransforms(source, targets, translate=True, rotate=True, scale=True):
```
#### Arguments
- source (str): The source transform.
- targets (list): A list of target transforms.
- translate (bool): Whether to translate the targets.
- rotate (bool): Whether to rotate the targets.
- scale (bool): Whether to scale the targets.

#### Returns
- N/A


### 🏷️ `FUNCTION` :: `getMMatrixFromList`

**Signature:**
```python
def getMMatrixFromList(matrixList):
```
#### Arguments
- matrixList (list): A list of floats representing a 4x4 matrix.

#### Returns
- An MMatrix object.


### 🏷️ `FUNCTION` :: `reorderMatrix`

**Signature:**
```python
def reorderMatrix(matrix, downAxis=0, upAxis=0):
```
#### Arguments
- matrix (MMatrix): The matrix to reorder.
- downAxis (int): The axis of the down vector.
- upAxis (int): The axis of the up vector.

#### Returns
- A reordered MMatrix object.


### 🏷️ `FUNCTION` :: `listFromMatrix`

**Signature:**
```python
def listFromMatrix(matrix):
```
#### Arguments
- matrix (MMatrix): The matrix to convert to a list.

#### Returns
- A list of floats representing the 4x4 matrix.


### 🏷️ `FUNCTION` :: `getWorldMatrix`

**Signature:**
```python
def getWorldMatrix(transform):
```
#### Arguments
- transform (str): The transform to get the world matrix for.

#### Returns
- The world matrix of the transform.


### 🏷️ `FUNCTION` :: `getObjectMatrix`

**Signature:**
```python
def getObjectMatrix(transform):
```
#### Arguments
- transform (str): The transform to get the object matrix for.

#### Returns
- The object matrix of the transform.