DATA: dict[str, list] = {
    "users": [
        {"_key": "1", "name": "Jane Smith", "age": 25, "gender": "Female"},
        {"_key": "2", "name": "Emily Davis", "age": 28, "gender": "Female"},
        {"_key": "3", "name": "John Doe", "age": 30, "gender": "Male"},
        {"_key": "4", "name": "Michael Johnson", "age": 35, "gender": "Male"},
        {"_key": "5", "name": "Emma Wilson", "age": 32, "gender": "Female"},
        {"_key": "6", "name": "David Smith", "age": 27, "gender": "Male"},
        {"_key": "7", "name": "Olivia Johnson", "age": 31, "gender": "Female"},
        {"_key": "8", "name": "James Davis", "age": 29, "gender": "Male"},
    ],
    "orders": [
        {
            "_key": "1",
            "user": "1",
            "order_date": "2023-05-01",
            "total_amount": 100.0,
            "products": ["1", "2"],
            "status": "COMPLETED",
        },
        {
            "_key": "2",
            "user": "1",
            "order_date": "2023-05-10",
            "total_amount": 50.0,
            "products": [],
            "status": "COMPLETED",
        },
        {
            "_key": "3",
            "user": "2",
            "order_date": "2023-05-05",
            "total_amount": 200.0,
            "products": [],
            "status": "COMPLETED",
        },
        {
            "_key": "4",
            "user": "3",
            "order_date": "2023-05-15",
            "total_amount": 150.0,
            "products": [],
            "status": "COMPLETED",
        },
        {
            "_key": "5",
            "user": "4",
            "order_date": "2023-05-03",
            "total_amount": 80.0,
            "products": [],
            "status": "COMPLETED",
        },
        {
            "_key": "6",
            "user": "5",
            "order_date": "2023-05-12",
            "total_amount": 120.0,
            "products": [],
            "status": "COMPLETED",
        },
        {
            "_key": "7",
            "user": "6",
            "order_date": "2023-05-07",
            "total_amount": 70.0,
            "products": [],
            "status": "COMPLETED",
        },
        {
            "_key": "8",
            "user": "7",
            "order_date": "2023-05-20",
            "total_amount": 90.0,
            "products": [],
            "status": "COMPLETED",
        },
    ],
    "products": [
        {"_key": "1", "name": "Product 1", "category": "Category A"},
        {"_key": "2", "name": "Product 2", "category": "Category B"},
        {"_key": "3", "name": "Product 3", "category": "Category A"},
        {"_key": "4", "name": "Product 4", "category": "Category C"},
        {"_key": "5", "name": "Product 5", "category": "Category B"},
        {"_key": "6", "name": "Product 6", "category": "Category A"},
        {"_key": "7", "name": "Product 7", "category": "Category C"},
    ],
    "reviews": [
        {"_key": "1", "product": "1", "user": "1", "rating": 4},
        {"_key": "2", "product": "1", "user": "2", "rating": 5},
        {"_key": "3", "product": "2", "user": "3", "rating": 3},
        {"_key": "4", "product": "3", "user": "4", "rating": 5},
        {"_key": "5", "product": "4", "user": "5", "rating": 4},
        {"_key": "6", "product": "5", "user": "6", "rating": 2},
        {"_key": "7", "product": "6", "user": "7", "rating": 5},
        {"_key": "8", "product": "7", "user": "8", "rating": 4},
    ],
}