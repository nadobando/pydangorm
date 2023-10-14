# **Operations**

## **ForOperation**

Represents the FOR operation in AQL, used to loop over sets of documents in a collection or the results of a subquery.
The class:

Takes parameters like `collection` or `variable` and `in` which specify what to loop over.
Contains an optional [`LoopOptions`](options.md#loopoptions-) parameter that can be used to specify loop-related options.

## **FilterOperation**

Represents the FILTER operation in AQL, used to filter the results of a query based on a condition.

## **SortOperation**

Represents the SORT operation in AQL, used to sort the results of a query.

The class can handle multiple sorts, specified as a list.
Each item in the list can be:

- **`FieldExpression`**
- tuple consisting of a field and sort direction. ("field", SortDirection.ASC)

## **InsertOperation**

Represents the **`INSERT`** operation in AQL.
This operation is used to insert a document into a collection.

It requires a doc parameter (the document to insert) and a collection parameter (the target collection).
The document can be provided as a dictionary, which is then converted to an ObjectExpression.

## **RemoveOperation**

Represents the REMOVE operation in AQL, which is used to remove a document from a collection.

The class sets:

- **`expression`**: **`Union[str, dict, LiteralExpression, FieldExpression, VariableExpression, ObjectExpression]`**,
- **`collection`**: **`Union[str, CollectionExpression]`**
- **`options`**: [**`Optional[RemoveOptions]`**](./options.md#removeoptions).

## **UpdateOperation**

Subclasses:

- **`BaseChangeOperation`**

Represents the UPDATE operation in AQL.

The parameters can be provided as dictionaries or **`ObjectExpression`**
The class sets:

- **`key`**: **`str`** or **`LiteralExpression`**
- **`obj`**: **`dict`** or **`ObjectExpression`**
- **`collection`** : **`str`** or **`CollectionExpression`**
- **`options`**: an optional [**`UpdateOptions`**](./options.md#updateoptions) parameter that can be used to specify update-related options.

## **ReplaceOperation**

Subclasses:

- **`BaseChangeOperation`**

The class sets:

- **`key`**: **`str`** or **`LiteralExpression`**
- **`obj`**: **`dict`** or **`ObjectExpression`**
- **`collection`** : **`str`** or **`CollectionExpression`**
- **`options`**: an optional [**`ReplaceOptions`**](./options.md#replaceoptions) parameter that can be used to specify update-related options.

Represents the REPLACE operation in AQL
The initialization parameters are the same as BaseChangeOperation.

## **UpsertOperation**

Represents the UPSERT operation in AQL.
This operation is used to insert a document if it doesn't exist or update/replace it if it does.

the class sets:

- **`filter_`**: the condition to match
- **`collection`**: the target collection
- **`insert`**: the document to insert if no match is found and either
- **`update`**: the data to update if a match is found
- **`replace`**: the document to replace if a match is found
- **`options`**: an optional [**`UpsertOptions`**](./options.md#upsertoptions) parameter that can be used to specify upsert-related options.

## **LetOperation**

Represents the LET operation in AQL,
which allows for the assignment of a value to a variable within a query.

## ReturnOperation

Represents the RETURN operation in AQL.

Takes a return_expr parameter that specifies what to return.
It can be a:

- collection
- list
- dictionary
  The **`distinct`** parameter allows for returning distinct values.

## LimitOperation

Represents the LIMIT operation in AQL, used to limit the number of results returned by a query.

Takes parameters like **`limit`** and **`offset`** to specify the number of results and the starting point.

## CollectOperation

Represents the COLLECT operation in AQL, which is used to group/aggregate results.

The class is initialized with various parameters, including:

- **`collect`**: Specifies the criteria for grouping results.
- **`aggregate`**: Specifies aggregate calculations to be performed on grouped results.
- **`into`**: Specifies the variable into which the grouped results are collected.
- **`keep`**: Specifies which variables to keep after the COLLECT operation.
- **`with_count_into`**: Specifies a variable that will store the number of grouped results.
- **`options`**: an optional [**`CollectOptions`**](./options.md#collectoptions) parameter that can be used to specify upsert-related options.

The compile method translates the COLLECT operation into its AQL representation,
incorporating the grouping criteria, aggregation calculations, and other parameters.

## **TraversalOperation**

Represents the graph traversal operation in AQL.

### TraversalDirection

An enumeration representing the traversal direction options in AQL graph queries. The options include:

- **`OUTBOUND`**
- **`INBOUND`**
- **`ANY`**

## Abstract Operations

### Operation

This is an abstract base class representing a generic AQL operation. The class:

Contains a **`query_ref`** attribute which refers to the broader query that the operation is a part of.
Provides an abstract compile method that subclasses need to implement to translate the operation
into its AQL representation.

### BaseChangeOperation

This is an abstract base class that provides common functionality for operations that change data in collections (e.g., UPDATE, REPLACE).

## Not Implemented Yet

### WindowOperation

Represents the WINDOW operation in AQL, which is used for windowed calculations on results.

### WithOperation

Represents the WITH operation in AQL.
