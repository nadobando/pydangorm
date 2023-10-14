## **`PydangoSession`**

### Overview

**`PydangoSession`** stands as the primary gateway for ORM-based interactions with ArangoDB. It wraps essential
functionalities, making database operations like initialization, querying, and document management seamless and
intuitive.

### Initialization:

The class can be instantiated with:

- a pre-configured StandardDatabase
- by providing details like client, database, username, and password.

!!! tip
Before using the session, ensure it's initialized by calling the initialize() method.

### Methods:

- **`initialize`**: Set up the session. Mandatory before performing database operations.
- **`create_indexes`**: Define and set up indexes for your models.
- **`save`**: Persist a document. The strategy parameter dictates the save behavior, whether to update
  existing or insert new.
- **`get`**: Fetch a document based on its model type and ID.
- **`execute`**: Directly run AQL queries.
