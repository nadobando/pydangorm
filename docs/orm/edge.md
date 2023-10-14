## **`EdgeModel`**

Metaclass: **`EdgeMeta`**

Subclasses:

- **`BaseArangoModel`**

### **Overview**

The **`EdgeModel`** class forms the foundational representation of an edge (relationship)
in ArangoDB within the pydango ORM.
It equips developers with the necessary attributes and methods to define and manage edges effectively.

### **Attributes**

- **`id`**: An optional unique identifier for the ArangoDB edge.
- **`key`**: An optional unique key specific to ArangoDB edges.
- **`rev`**: An optional revision attribute used in ArangoDB for versioning and conflict resolution.
- **`from_`**: Represents the starting vertex of the edge. Aliased to **`FROM`** for ArangoDB compatibility.
- **`to`**: Depicts the target vertex of the edge. Aliased to `TO` for compatibility.
- **`Config`**: Inherits from `BaseConfig`, providing **`Pydantic`** model-specific configurations.
- **`Collection`**: A subclass that inherits from **`EdgeCollectionConfig`**, offering edge-specific collection configurations
  for the  ORM.

## **`EdgeCollectionConfig`**

Subclasses:

- **`CollectionConfig`**

### Overview

The **`EdgeCollectionConfig`** class provides configurations tailored specifically for edge collections in ArangoDB. By
extending the base CollectionConfig,
