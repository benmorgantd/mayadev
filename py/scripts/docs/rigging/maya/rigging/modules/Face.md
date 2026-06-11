Here is the Markdown documentation for the `Face` module:

# Module: Face

### Pipeline Intent
The "Face" module is responsible for setting up facial rigging components and hierarchies.

### Technical Implementation
This module imports necessary modules from the `bmaya` package, including `module`, `shapelib`, and `nameUtils`. It defines a class `Face` that inherits from `module.Module`.

#### Methods

- **`__init__`**: Initializes the Face module with various parameters and sets up its components.
- **`build`**: Builds the facial rig hierarchy by creating drive joints, bind joints, and controls for each region of the face (upper head, middle head, lower head, jaw, eyes, eyebrows).
- **`buildFaceFkHierarchy`**: A helper method that recursively finds hierarchy joints, creates drive joints and controls, and binds them to the facial rig.

### Overview
The `Face` module sets up a hierarchical structure for facial rigging, allowing for control over various regions of the face (upper head, middle head, lower head, jaw, eyes, eyebrows). It uses the `FkChain` class from the `bmaya.maya.rigging.modules.FkChain` module to create drive joints and controls.

### Cross-Module Dependencies
* **Internal Framework Links:** `module`, `shapelib`, `nameUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### CLASS :: Face

**Purpose:** Initializes and sets up facial rigging components and hierarchies.

**Methods:**

- **`__init__`**: Initializes the Face module with various parameters and sets up its components.
- **`build`**: Builds the facial rig hierarchy by creating drive joints, bind joints, and controls for each region of the face (upper head, middle head, lower head, jaw, eyes, eyebrows).
- **`buildFaceFkHierarchy`**: A helper method that recursively finds hierarchy joints, creates drive joints and controls, and binds them to the facial rig.

---

I hope this meets your requirements! Let me know if you need any further assistance.