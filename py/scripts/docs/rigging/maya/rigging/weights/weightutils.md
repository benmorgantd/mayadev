# Module: weightutils

### Pipeline Intent
Provides utility functions for working with skin clusters and weights in Maya.

### Technical Implementation
The `weightutils` module contains various functions for interacting with skin clusters, their weights, and influences. These functions are designed to simplify common tasks related to character rigging and skinning in Maya.

### Overview
This module offers several key features:

* Functions for finding the skin cluster deforming a mesh (`getSkinClusterName`, `getSkinClusterObj`)
* Utilities for getting and setting skin cluster weights (`getSkinClusterWeights`, `setSkinClusterWeights`)
* Pruning of weight lists to reduce influence count (`pruneWeightList`, `pruneSkinWeights`)
* Conversion of Delta Mush to skin cluster weights (`bakeDeltaMushToSkinCluster`)

### Cross-Module Dependencies

* **Internal Framework Links:** None
* **External Dependencies:** Maya.cmds, OpenMaya, PyMel