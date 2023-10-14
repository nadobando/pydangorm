## **`VertexModel`**

Metaclass: **`VertexMeta`**

Subclasses: **`BaseArangoModel`**

### **Overview**

The `VertexModel` class represents a vertex in the context of the `pydango` ORM. It provides essential attributes,
methods, and configurations for defining and working with vertices in ArangoDB.

### **Attributes**

- **`id`**: An optional unique identifier for the ArangoDB vertex.
- **`key`**: An optional unique key specific to ArangoDB vertices.
- **`rev`**: An optional revision attribute used in ArangoDB for versioning and conflict resolution.
- **`edges`**: Represents the edges related to this vertex. Allows for dot-notation access to related edges.
- **`Config`**: Inherits from `BaseConfig`, providing Pydantic model-specific configurations.
- **`Collection`**: Inherits from `VertexCollectionConfig`, offering vertex-specific collection configurations.

## **Collection**

### **`VertexCollectionConfig`**

Subclasses:

- **`CollectionConfig`**

### **Overview**

The `VertexCollectionConfig` class provides specific configurations tailored for vertex collections in ArangoDB. It
extends the base `CollectionConfig` with vertex-centric customizations.
