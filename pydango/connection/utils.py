from typing import TYPE_CHECKING, Awaitable, Optional, Type, Union, cast, overload

import aioarango

if TYPE_CHECKING:
    from aioarango import ArangoClient
    from aioarango.collection import StandardCollection
    from aioarango.database import StandardDatabase

    from pydango.orm.models import BaseArangoModel


@overload
async def get_or_create_collection(
    db: "StandardDatabase", model: Type["BaseArangoModel"], *, edge=None
) -> "StandardCollection":
    ...


@overload
async def get_or_create_collection(db: "StandardDatabase", model: str, *, edge=None) -> "StandardCollection":
    ...


async def get_or_create_collection(
    db: "StandardDatabase", model: Union[str, Type["BaseArangoModel"]], *, edge: Optional[bool] = None
) -> "StandardCollection":
    if isinstance(model, str):
        collection_name = model
        edge = edge or False
    elif collection := getattr(model, "Collection", None):
        collection_name = collection.name
        if edge is None:
            edge = True if collection.type.value == collection.type.EDGE else False
    else:
        raise AssertionError()

    if not await db.has_collection(collection_name):
        try:
            return await cast(Awaitable["StandardCollection"], db.create_collection(collection_name, edge=edge))
        except aioarango.exceptions.CollectionCreateError as e:
            if e.error_code != 1207:
                raise e

    return db.collection(collection_name)


async def get_or_create_db(client: "ArangoClient", db: str, user: str = "", password: str = "") -> "StandardDatabase":
    sys_db = await client.db("_system", username=user, password=password)

    if not await sys_db.has_database(db):
        await sys_db.create_database(db)

    return await client.db(db, username=user, password=password)


async def deplete_cursor(cursor):
    result = []
    while cursor.has_more():  # Fetch until nothing is left on the server.
        await cursor.fetch()
    while not cursor.empty():  # Pop until nothing is left on the cursor.
        result.append(cursor.pop())
    return result


async def iterate_cursor(cursor):
    return [doc async for doc in cursor]
