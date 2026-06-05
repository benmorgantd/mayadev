Here is the Markdown documentation for this file:

# Module: bm_softCluster

### Pipeline Intent
Automates the creation of a soft cluster deformer, mirroring the weights of the soft selection. Designed to streamline character rigging performance workflows.

### Technical Implementation
Uses Maya's OpenMaya and cmds modules to gather information about the selected mesh or lattice, then creates a corresponding soft cluster deformer. This allows animators to quickly generate clusters based on their soft selections.

### Overview
This module provides an API-based implementation of the soft cluster deformer, leveraging OpenMaya and Maya's internal APIs for efficient data retrieval and manipulation.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.weights.skin.averageVertexSkinWeightCmd`, `bmaya.maya.rigging.weights.skin.bm_copyWeights`, `bmaya.maya.rigging.weights.skin.bm_extrude_weights`, `bmaya.maya.rigging.weights.skin.bm_pruneSkinWeightsPlugin`
* **External Dependencies:** Maya.cmds, OpenMaya

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `softCluster`
**Signature:**
```python
def softCluster():
```
#### Description:
Creates a soft cluster deformer based on the selected mesh or lattice, mirroring its weights.

#### Returns:
The newly created soft cluster deformer.