# Options

A Base class representing general AQL options.
Some AQL Operations have options that can be passed to them. to configure how the operation is performed.

## **LoopOptions**

Represents options specific to loops in AQL. The options include:

- **`index_hint`**: A hint for which index to use.
- **`force_index_hint`**: Whether to force the use of the index hint.
- **`disable_index`**: If set, disables the use of indexes.
- **`max_projections`**: Maximum number of projections.
- **`use_cache`**: Indicates if caching should be used.
- **`look_ahead`**: The number of lookahead operations.

## **ModificationOptions**

### BaseModificationOptions

An abstract base class representing options for modification operations in AQL.
The options include:

- **`ignore_errors`**: Whether to ignore errors.
- **`wait_for_sync`**: If set, waits for synchronization.
- **`ignore_revs`**: Ignores revisions.
- **`exclusive`**: Not fully described in the current snippet.
- **`refill_index_caches`**: Refills index caches if set.

### **RemoveOptions**

Subclasses:

- **`BaseModificationOptions`**

Represents options for the remove operation in AQL.

### **UpdateOptions**

Subclasses:

- **`BaseModificationOptions`**

The options include:

- **`keep_null`**: If set, retains null values.
- **`merge_objects`**: If set, merges objects.
- **`refill_index_caches`**: Refills index caches if set.

### **ReplaceOptions**

Subclasses:

- **`BaseModificationOptions`**

Represents options for the replace operation in AQL.

### **UpsertOption**

Subclasses:

- **`BaseModificationOptions`**

The options include:

- **`index_hint`**: hint for which index to use.

## **CollectOptions**

Represents options specific to the COLLECT operation in AQL.
The options include:

- **`method`**: Specifies the method used for the COLLECT operation **`CollectMethod`**

### CollectMethod

An enumeration representing the method used for the COLLECT operation in AQL.
The values include:

- **`SORTED`**
- **`HASHED`**
