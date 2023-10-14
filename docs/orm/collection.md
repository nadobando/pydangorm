## **`CollectionConfig`**

The `CollectionConfig` class provides configuration specific to an ArangoDB collection. It defines attributes that
represent various settings and configurations for a collection in ArangoDB, allowing developers to fine-tune collection
behavior.

### **Attributes**

- **`name`**: The name of the ArangoDB collection.
- **`type`**: The type of the collection, represented as an enum (`CollectionType`).
- **`sync`**: A boolean indicating whether to synchronize the collection. Default is `False`.
- **`system`**: A boolean indicating if the collection is a system collection. Default is `False`.
- **`key_generator`**: Specifies the type of key generation strategy. Possible values are "traditional" and "
- **`autoincrement`**". Default is "traditional".
- **`user_keys`**: A boolean indicating whether user-generated keys are allowed. Default is `False`.
- **`key_increment`**: An integer specifying the increment value for auto-incrementing keys.
- **`key_offset`**: An integer specifying the offset value for auto-incrementing keys.
- **`shard_fields`**: A list of fields that determine the sharding strategy.
- **`shard_count`**: An integer indicating the number of shards for the collection.
- **`replication_factor`**: An integer specifying the replication factor for the collection.
- **`shard_like`**: A string representing another collection to use as a sharding reference. Available in enterprise
- editions only.
- **`sync_replication`**: A boolean indicating whether to synchronize replication.
- **`enforce_replication_factor`**: A boolean indicating whether to enforce the specified replication factor.
- **`sharding_strategy`**: Specifies the sharding strategy. Possible values include "community-compat", "
  enterprise-smart-edge-compat", and "enterprise-smart-edge".
- **`smart_join_attribute`**: A string specifying the attribute used for smart joins. Available in enterprise editions
  only.
- **`write_concern`**: An integer indicating the level of write concern for the collection.
- **`sync_schema`**: A boolean indicating whether to synchronize the schema. Default is `False`.
- **`indexes`**: A sequence of index configurations [**`Indexes`**](#indexes) for the collection. Default is an empty list.

### **Tips for Developers**

## **Indexes**

### Overview

The indexes module offers a suite of classes to define and work with various types of indexes in ArangoDB collections,
optimizing query performance.

### Indexes

- **`GeoIndex`**: Define geospatial indexes for querying based on geographical locations.
- **`HashIndex`**: Craft hash indexes for rapid equality-based lookups.
- **`SkipListIndex`**: Ideal for range queries, providing a range-based indexing mechanism.
- **`FullTextIndex`**: Optimize your text-based queries with this full-text search index.
- **`PersistentIndex`**: Ensures the index remains stored on disk for persistence.
- **`TTLIndex`**: Automatically remove documents post a specified time with this Time-To-Live index.

!!! tip
Tips for Developers

1. When setting up a collection in ArangoDB through the ORM, utilize the `CollectionConfig` class to customize
   collection behavior.
1. Ensure that the `name` attribute is set, as it determines the name of the collection in ArangoDB.
1. If using the enterprise edition of ArangoDB, consider leveraging the enterprise-specific attributes like `shard_like`
   and `smart_join_attribute` for advanced configurations.
1. Adjust the `indexes` attribute to define specific indexes on the collection for optimized queries.
1. Determine the nature of your queries to select the appropriate index type. For instance, use GeoIndex for location-based
   queries and FullTextIndex for textual searches.
1. Always specify the fields attribute when defining an index, as it determines which fields in the collection the index
   applies to.
1. Consider using the `in_background` attribute if you want to create the index without blocking other operations.
