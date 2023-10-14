# **Query**

The pydango/query package provides a comprehensive and Pythonic interface for constructing and executing queries on
ArangoDB. It abstracts the complexities of direct AQL (ArangoDB Query Language) and offers a structured approach to
build both simple and complex queries with ease.

### **AQLQuery**

#### **Introduction**

The `AQLQuery` class offers a flexible and Pythonic interface for constructing, managing, and preparing AQL queries. It provides methods corresponding to a variety of AQL operations, allowing users to create complex queries by chaining these operations together.

#### Class Attributes:

- `_ops`: A list of operations associated with the query.
- `sep`: Specifies the separator between different parts of the query.
- `bind_vars`, `compiled_vars`, `__dynamic_vars__`, `__used_vars__`: Various attributes related to variables and their management within the query.
- `_parameters`: Holds query parameters.
- `_var_counter`, `_param_counter`: Counters for generating unique variable and parameter names.
- `parent`: Reference to a parent `AQLQuery`, if any.
- `__is_modification_query__`: Boolean indicating if the query modifies data.

#### Methods:

##### **`for_`**

`for_(self, collection_or_variable, in_: Expression) -> 'AQLQuery'`
Adds a [**`FOR`**](./operations.md#foroperation) operation to the query.  Iterates over a collection or variable.

##### **`filter`**

`filter(self, filter_expr: Expression) -> 'AQLQuery'`
Adds a [**`FILTER`**](./operations.md#filteroperation) operation to the query. Filters the results of a query based on a condition.

##### **`sort`**

`sort(self, *args: Expression) -> 'AQLQuery'`
Adds a [**`SORT`**](./operations.md#sortoperation) operation to the query. Sorts the results of a query based on provided parameters.

##### **`let`**

`let(self, variable: Union[str, VariableExpression], value: Expression) -> Union[VariableExpression, 'AQLQuery']`
Adds a [**`LET`**](./operations.md#letoperation) operation to the query. Defines a variable within the query.

##### **`return_`**

`return_(self, return_expr: Expression) -> 'AQLQuery'`
Adds a [**`RETURN`**](./operations.md#returnoperation) operation to the query. Specifies the return value of the query.

##### **`limit`**

`limit(self, limit: int, offset: Optional[int] = None) -> 'AQLQuery'`
Adds a [**`LIMIT`**](./operations.md#limitoperation) operation to the query. Limits the number of results returned by the query.

##### **`insert`**

`insert(self, doc: Dict[str, Any], collection: str) -> 'AQLQuery'`
Adds an [**`INSERT`**](./operations.md#insertoperation) operation to the query. Inserts a document into a collection.

##### **`remove`**

`remove(...) -> 'AQLQuery'`
Adds a [**`REMOVE`**](./operations.md#removeoperation) operation to the query. Removes documents from a collection.

##### **`update`**

`update(...) -> 'AQLQuery'`
Adds an [**`UPDATE`**](./operations.md#updateoperation) operation to the query. Updates documents in a collection.

##### **`replace`**

`replace(...) -> 'AQLQuery'`
Adds a [**`REPLACE`**](./operations.md#replaceoperation) operation to the query. Replaces documents in a collection.

##### **`upsert`**

`upsert(...) -> 'AQLQuery'`
Adds an [**`UPSERT`**](./operations.md#upsertoperation) operation to the query. Inserts or updates documents in a collection.

##### **`collect`**

`collect(...) -> 'AQLQuery'`
Adds a [**`COLLECT`**](./operations.md#collectoperation) operation to the query. Collects documents from a collection.

##### **`traverse`**

`traverse(...) -> 'AQLQuery'`
Creates a [**`TRAVERSE`**](./operations.md#traverseoperation) operation. Traverses a graph.

##### **`prepare`**

`prepare() -> PreparedQuery`
Prepares the query for execution, returning a `PreparedQuery` instance.

### **PreparedQuery**

#### Introduction

The PreparedQuery class represents a prepared AQL query ready for execution against an ArangoDB instance. It encapsulates the AQL query string and any bind variables that need to be provided alongside the query.

#### Class Attributes:

- **`query`**: A string that holds the AQL query.
- **`bind_vars`**: A dictionary of variables to be bound to the query. These are represented in a JSON-compatible format.
