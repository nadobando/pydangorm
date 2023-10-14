## **Introduction**

`pydangorm` is a robust and user-friendly **asynchronous** ORM (Object-Relational Mapping) system tailored
for [ArangoDB](https://arangodb.com/), a powerful
multi-model NoSQL database.

`pydangorm` is inspired by `SQLAlchemy`, a popular ORM system for SQL databases, It aims to provide a similar experience

## **Main Libraries**

`pydangorm` is built upon the foundation of two primary libraries:

- **pydantic**: An extremely popular data validation and settings management library for Python. In `pydangorm`,
  pydantic is utilized to provide robust model definitions and validation, ensuring that data interactions are clean,
  consistent, and error-free.

- **aioarango**: An asynchronous driver for ArangoDB. It powers the core interactions with the ArangoDB database, making
  it possible for `pydangorm` to support asynchronous database operations, ensuring optimized I/O-bound tasks.

## **Features**

- **Database Modeling**: Easily define, validate, and interact with your database models. This includes
  support for both vertex and edge models (`VertexModel` and `EdgeModel`).

- **Pythonic Query Building**: Constructing queries for ArangoDB in a **SQLAlchemy** way. With a Pythonic API, you can
  effortlessly build complex queries to retrieve or manipulate your data.

- **Session Management**: Manage your database sessions and connections with ease. Whether it's connecting to the
  database or handling transactions, `pydangorm` has got you covered.

- **Collection Management**: From creating indices to truncating collections, manage all your collection operations
  without hassle.

- **Asynchronous Support**: `pydangorm` is designed for the modern web. With full asynchronous support, your I/O-bound
  database tasks will be lightning fast, ensuring your applications remain responsive and scalable.

- **Lazy Loading**: `pydangorm` supports lazy loading, ensuring that data is only fetched when needed, optimizing
  performance and reducing memory usage.

### **Roadmap**

- [x] Support for **`AQL Query Building including trversal`**
- [x] Support for **`VertexModel`** and **`EdgeModel`**
- [x] Support for **`VertexModel`** relationships via **`EdgeModel`**
- [x] Support for **`Model Saving and Updating (single instance)`**
- [x] Support for **`Model Saving and Updating (with relations)`**
- [x] Support for **`Model Deletion (single instance)`**
- [x] Support for **`Model Fetching (single instance)`**
- [x] Support for **`Model Fetching with relations and traversal`**
- [x] Support for **`Model Graph CRUD Operations`**
- [ ] Support for **`Model Deletion Cascade`**
- [ ] Support for **`pydantic` `v2.0`**
- [ ] Support for **`Model Back Population`**

______________________________________________________________________

### **Contributions**

We're actively looking for contributors to help improve pydangorm and expand its capabilities.

Whether you're a seasoned
developer or just starting out, your contributions are valuable to us. If you have ideas for new features,
optimizations, or simply want to fix a bug, please check our contribution guidelines or reach out. Together, we can make
pydangorm the best ArangoDB ORM for Python!
