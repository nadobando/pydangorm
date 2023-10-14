# Functions

## **Abstract Functions**

### **`BaseFunctionExpression`**

This is an abstract base class that represents a generic AQL function.
handles the compilation of the function into its AQL representation.
Takes a function name and a list of arguments.

Converts dictionaries and lists to their respective ObjectExpression and ListExpression representations.

### **`FunctionExpression`**

Subclasses:

- **`BaseFunctionExpression`**
- **`ReturnableExpression`**

It represents an AQL function that can be used/returned in a query.
It enforces that a valid function name is provided.

### **`ReturnsArray`**

An abstract base class that mark functions that return arrays.

## **Document Functions**

### **`Document`**

Represent the DOCUMENT AQL function, which retrieves a document by its ID.

### **`Unset`**

Represent the UNSET AQL function.

```AQL
UNSET(document, attributeName1, attributeName2, ... attributeNameN)
```

Remove the attributes `attributeName1` to `attributeNameN` from document.
All other attributes will be preserved.

### **`Merge`**

Represents the MERGE AQL function.

```AQL
MERGE(document1, document2, ... documentN)
```

Merge the documents `document1` to `documentN` into a single document.

### **`Has`**

Represents the HAS AQL function.

```AQL
HAS(document, attributeName)
```

This function checks if an attribute exists in a given document.

## **List/Array Functions**

### **`Length`**

Represents the LENGTH AQL function.

```
LENGTH(anyArray)
```

It has some additional functionality that allows arithmetic operations like addition and subtraction on the result.

### **`Append`**

Represents the APPEND AQL function. This function appends a value to an array.

### **`Concat`**

Represents the CONCAT AQL function. It concatenates multiple arrays into one.

### **`Count`**

Represents the COUNT AQL function. It counts the number of items in an array.

## **Numeric Functions**

### **`Sum`**

Represents the **`SUM`** AQL function.

## **String Functions**

### **`RegExMatch`**

Represents the REGEX_MATCHES AQL function. This function matches a string against a regular expression pattern.

## **Misc Functions**

### **`CollectionsExpression`**

```AQL
COLLECTIONS()
```

Represents the COLLECTIONS AQL function. This function likely retrieves information about all collections.
