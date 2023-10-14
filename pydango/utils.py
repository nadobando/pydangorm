import asyncio
from typing import TYPE_CHECKING, Type, cast

from aioarango.database import StandardDatabase

from pydango.connection.exceptions import SessionNotInitializedError
from pydango.connection.utils import get_or_create_collection

if TYPE_CHECKING:
    from pydango import PydangoSession
    from pydango.orm.models.base import ArangoModel


async def init_model(model: type["ArangoModel"], session: "PydangoSession"):
    if not session.initialized:
        raise SessionNotInitializedError()

    collection = await get_or_create_collection(cast(StandardDatabase, session.database), model)
    await session.create_indexes(collection, model)


async def init_models(session: "PydangoSession", *models: Type["ArangoModel"]):
    if not session.initialized:
        raise SessionNotInitializedError()
    await asyncio.gather(*[init_model(coll, session) for coll in models])
