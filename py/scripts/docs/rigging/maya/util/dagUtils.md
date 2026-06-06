# Module: dagUtils

### Pipeline Intent
Provides utility functions for working with the DAG in Maya. These are used by various components to perform common tasks on DAG nodes, such as getting children, parents, etc.

### Technical Implementation
Exposes a set of Python functions that interact with Maya's Command Language (maya.cmds) to retrieve and manipulate DAG nodes. Utilizes Maya's built-in functionality for listing relatives and converting node types.

### Overview
The dagUtils module offers three primary functions: `getChildren`, `getAllChildren`, and `getParent`. These methods enable developers to efficiently navigate the DAG, retrieving specific types of nodes or traversing entire child hierarchies.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** maya.cmds

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `getChildren`
**Signature:**
```python
def getChildren(dagNode, ofType=None, allDescendents=False):
```
#### Arguments
- dagNode (str): The DAG node to retrieve children from.
- ofType (optional, str): Filter by the specified node type.
- allDescendents (boolean, optional): Retrieve children of all descendant nodes.

#### Returns
- List of child nodes or an empty list if none found.

---

### 🏷️ `FUNCTION` :: `getAllChildren`
**Signature:**
```python
def getAllChildren(dagNode, ofType=None):
```
#### Arguments
- dagNode (str): The DAG node to retrieve all children from.
- ofType (optional, str): Filter by the specified node type.

#### Returns
- List of child nodes or an empty list if none found. This is equivalent to calling `getChildren` with `allDescendents=True`.

---

### 🏷️ `FUNCTION` :: `getParent`
**Signature:**
```python
def getParent(dagNode, ofType=None):
```
#### Arguments
- dagNode (str): The DAG node to retrieve the parent from.
- ofType (optional, str): Filter by the specified node type.

#### Returns
- Parent node as a string or None if no parent found.