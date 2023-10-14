## **AQLQuery**

### 1. Simple Query to Fetch Data

```python
from pydango.query import AQLQuery

# Constructing a query to fetch all users from the "users" collection
query = AQLQuery().for_("user", "users").return_("user")

# Preparing and printing the query
prepared = query.prepare()
print(prepared.query)
```

Equivalent to:

```python
from pydango.query import AQLQuery
from pydango.query.expressions import IteratorExpression, CollectionExpression

# Constructing a query to fetch all users from the "users" collection
iterator = IteratorExpression("user")
query = AQLQuery().for_(iterator, CollectionExpression("users")).return_(iterator)

# Preparing and printing the query
prepared = query.prepare()
print(prepared.query)
```

### 2. Filtering Data with Conditions

```python
from pydango.query.expressions import IteratorExpression

# Fetching users aged 30 from the "users" collection
user = IteratorExpression("user")
query = AQLQuery().for_(user, "users").filter(user.age == 30).return_(user)

# Preparing and printing the query
prepared = query.prepare()
print(prepared.query)
```

### 3. Sorting and Limiting Results

```python
from pydango.query.expressions import IteratorExpression
from pydango.query.operations import AQLQuery

# Fetching top 10 users sorted by their names
user = IteratorExpression("user")

query = AQLQuery().for_(user, "users").sort(+user.name).limit(10).return_(user)

# Preparing and printing the query
prepared = query.prepare()
print(prepared.query)
```

### 4. Inserting Data

```python
from pydango.query.expressions import NEW
from pydango.query.operations import AQLQuery

new_user = {"name": "John Doe", "age": 25, "email": "john@example.com"}

# Inserting a new user into the "users" collection
query = AQLQuery().insert(new_user, "users").return_(NEW()._id)

# Preparing and printing the query
prepared = query.prepare()
print(prepared.query)
```

### 5. Complex Query: Aggregation and Grouping

```python
from pydango.query.expressions import VariableExpression, AssignmentExpression
from pydango.query.operations import AQLQuery

user = VariableExpression("users")
category_collect = VariableExpression("categoryCollect")
groups = VariableExpression("groups")

# Grouping users by category
query = (
    AQLQuery()
    .for_(user, "users")
    .collect(collect=AssignmentExpression(category_collect, user.category), into=groups)
    .return_({"groups": groups, "categories": category_collect})
)

# Preparing and printing the query
prepared = query.prepare()
print(prepared.query)
```
