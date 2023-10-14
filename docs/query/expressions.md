# Expressions

## **Basic Expressions**

### **`CollectionExpression`**

Subclasses:

- **`IterableExpression`**

Represents ArangoDB collections in AQL queries. It takes a collection name and an optional iterator.
It provides methods for accessing fields within the collection and compiles the collection name into its AQL
representation.

### **`LiteralExpression`**

Represents literal expressions in `AQL`. Inherits from BindableExpression and have a
representation as **`?`**, which is likely a placeholder for a value to be bound later.

### **`FieldExpression`**

Represents field accesses in `AQL` queries. This class handles accessing fields or attributes of
documents or objects within queries. It provides functionalities like:

Accessing nested fields.
Generating proper `AQL` syntax for field access.
Overloaded operators to produce conditional expressions. This allows users to write Pythonic
expressions for arithmetic operations (**`+`**, **`-`**, **`*`**, **`/`**, **`%`**) and
comparisons (**`==`**, **`>`**, **`<`**, **`>=`**, **`<=`**),
which get translated into corresponding `AQL` expressions.

### **`VariableExpression`**

Represents variable expressions in `AQL`. This class allows for dynamic variable names and access to
fields within the variable.

### **`IteratorExpression`**

This class inherits from **VariableExpression** and represent an iterator in AQL queries.
Iterators are used in FOR loops in AQL to iterate over a set of values or documents.

## **FigurativeExpression**

Subclasses:

- **`BindableExpression`**
- **`ReturnableExpression`**

Abstract class for non `LiteralExpression`

### **`ListExpression`**

Subclasses:

- **`BindableExpression`**
- **`ReturnableExpression`**

Represents lists in AQL. This class can take a variety of item types, including:

- query expressions
- literals
- mappings
- sequences
- basic data types like int, float, str, and bool.

Handles nested structures, converting nested lists into appropriate AQL representations.

### **`ObjectExpression`**

Represents objects (like dictionaries or AQL documents) in queries.
This class Can take a variety of key-value pairs, including:

- query expressions
- literals
- mappings
- sequences
- basic data types like int, float, str, and bool.

Handles nested structures, converting nested dictionaries and lists into appropriate AQL representations.
Possesses a \_bind attribute for binding values to the object.

## **Iterable Expressions**

### **`RangeExpression`**

Represents a range in AQL queries, such as specifying a range of numbers. It support both
literal values and other expressions for the start and end of the range.

### **`AssignmentExpression`**

Represents an assignment operation in AQL, like setting a variable's value.

## **Binary Expressions**

### **`BinaryLogicalExpression`**

A subclass of ConditionExpression that represents binary logical operations in AQL. The comment
suggests it supports operations like **`&&`** (AND) and **`||`** (OR).

### **`BinaryArithmeticExpression`**

## **Unary Logical Expressions**

This class might represent unary logical operations, though specific operations aren't immediately clear from this
snippet. **`NOT`**

### **`NotExpression`**

represents the **`NOT`** operation in AQL.

## **BinaryLogicalExpression**

### **`AndExpression`**

Subclasses of BinaryLogicalExpression that represent the logical AND (&&)
operations, respectively.

### **`OrExpression`**

represent the logical OR (||) operations.

### **`ConditionExpression`**

Inherits from BinaryExpression and LogicalExpression. This class represent conditional
operations in AQL, like comparisons (e.g., `>`, `>=`, `==`, `!=`, `<`, `<=`).
It also supports chaining of conditions using logical operators `AND` and `OR`.

### **`In`**

A subclass of ConditionExpression that represent the **`IN`** operation in AQL, where an object is checked if
it's part of an iterable.

## **Arithmetic Expressions**

### **`UnaryArithmeticExpression`**

Inherits from both UnaryExpression and BaseArithmeticExpression. This class represents unary
arithmetic operations in AQL. **`-1`**

### **`ArithmeticExpression`**

Inherits from both BinaryExpression and BaseArithmeticExpression. Represents binary arithmetic
operations in AQL. It also has overloaded comparison operators to form conditions from arithmetic results.

## **Query Expressions**

### **`QueryExpression`**

An abstract base class that represents an AQL Query.

### **`SubQueryExpression`**

Represents subqueries in AQL. Subqueries are queries embedded within other queries. This class wraps
around another QueryExpression to represent the subquery. The compile method seems to format the subquery for inclusion
in the main query.

## **Query Result Expressions**

### **`ScalarSubQuery`**

Inherits from SubQueryExpression. The details aren't fully visible, but this might represent a subquery
that returns a scalar value.

### **`VectorSubQueryExpression`**

Inherits from both SubQueryExpression and IterableExpression. This class likely represents
subqueries that return a list or array of results.

## **Modification Variables**

### **`NEW`**

A subclass of ModificationVariable representing the "NEW" keyword in `AQL`, which might be used to refer to the new
version of a document after an update or replace operation.

### **`OLD`**

A subclass of ModificationVariable represents the "OLD" keyword in `AQL`, likely referring to the
previous version of a document before an update or replace operation.

## **Sort Expressions**

### **`SortExpression`**

Represents a `SORT` expression in `AQL`. This class handles sorting of query results.

#### **SortDirection**

An enumeration defining sorting directions - ASC for ascending and DESC for descending.

## **Abstract Expressions**

### **`Expression`**

An abstract base class for all types of expressions. It mandates an abstract method compile which would be
essential for turning the Pythonic expression into `AQL` syntax.

### **`BindableExpression`**

A subclass of Expression which appears to represent expressions that can be bound to specific values.

### **`ReturnableExpression`**

An abstract base class representing returnable expressions. This might be a base for expressions that
can be part of the RETURN statement in `AQL`.

### **`IterableExpression`**

An abstract base class that represents an iterable expressions in AQL.

### **`ModificationVariable`**

Subclasses:
**`VariableExpression`**

variables used in modification queries (like `UPDATE`, `INSERT`, `UPSERT`, `REPLACE`).

### **`ReturnableIterableExpression`**

Subclasses:

- **`IterableExpression`**
- **`ReturnableExpression`**

This class marks that some iterable expressions can be returned in AQL queries.

### **`UnaryExpression`**

Represents unary operations in AQL queries, like NOT or negation.

### **`BinaryExpression`**

Represents binary operations in AQL queries, such as arithmetic operations (like addition or
multiplication) or logical operations (like `AND` or `OR`).

### **`LogicalExpression`**

An abstract base class representing logical expressions in AQL queries. This serves as a foundational
class for both unary and binary logical operations.

### **`BaseArithmeticExpression`**

Abstract base class for arithmetic operations
