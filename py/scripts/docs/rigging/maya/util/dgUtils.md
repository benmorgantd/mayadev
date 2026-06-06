# Module: dgUtils

### Pipeline Intent
Provides utility functions for working with the Maya DAG, enabling various components to perform common tasks on DG nodes.

### Technical Implementation
Utilizes the Maya `cmds` module to interact with the scene graph. Handles node retrieval and filtering based on type specifications.

### Overview
The dgUtils module offers a set of utility functions for interacting with the Maya Digital Asset Graph (DAG). These functions are designed to simplify common tasks, such as retrieving nodes in the scene or listing attribute connections.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** maya.cmds

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `getNodesInScene`
**Signature:**
```python
def getNodesInScene(ofType=None):
```
#### Arguments
- ofType (type): Optional type specification for the nodes to retrieve.

#### Returns
- A list of nodes in the scene, filtered by type if specified.

---

### TODO: attribute connections

Note: The TODO comment indicates a pending feature development task.