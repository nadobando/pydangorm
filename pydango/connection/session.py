import asyncio
import dataclasses
import json
import logging
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
    overload,
)

from aioarango import ArangoClient
from aioarango.collection import Collection, StandardCollection
from aioarango.database import StandardDatabase
from aioarango.exceptions import AQLQueryExecuteError
from aioarango.result import Result
from aioarango.typings import Json

from pydango.connection.consts import PYDANGO_SESSION_KEY
from pydango.connection.exceptions import (
    DocumentNotFoundError,
    SessionNotInitializedError,
)
from pydango.connection.graph_utils import db_traverse, graph_to_document
from pydango.connection.query_utils import (
    _build_graph_query,
    _get_upsert_filter,
    _make_upsert_query,
)
from pydango.connection.types import CollectionUpsertOptions, UpdateStrategy
from pydango.connection.utils import get_or_create_db
from pydango.indexes import (
    FullTextIndex,
    GeoIndex,
    HashIndex,
    Indexes,
    PersistentIndex,
    SkipListIndex,
    TTLIndex,
)
from pydango.orm.models import BaseArangoModel, VertexModel
from pydango.orm.query import ORMQuery
from pydango.query import AQLQuery
from pydango.query.expressions import IteratorExpression, VariableExpression
from pydango.query.functions import Document
from pydango.query.operations import TraversalDirection
from pydango.query.query import TraverseIterators

if TYPE_CHECKING:
    from pydango.orm.models.base import ArangoModel
    from pydango.orm.models.vertex import TVertexModel

logger = logging.getLogger(__name__)
_INDEX_MAPPING: dict[Type[Indexes], Callable[..., Awaitable["Result[Json]"]]] = {
    GeoIndex: Collection.add_geo_index,
    HashIndex: Collection.add_hash_index,
    SkipListIndex: Collection.add_skiplist_index,
    FullTextIndex: Collection.add_fulltext_index,
    PersistentIndex: Collection.add_persistent_index,
    TTLIndex: Collection.add_ttl_index,
}


def _collection_from_model(database: StandardDatabase, model: Type[BaseArangoModel]) -> StandardCollection:
    return database.collection(model.Collection.name)


class PydangoSession:
    @overload
    def __init__(self, *, database: StandardDatabase): ...

    @overload
    def __init__(
        self, *, client: ArangoClient, database: str, username: str = "", password: str = "", auth_method: str = "basic"
    ): ...

    def __init__(
        self,
        *,
        client: Optional[ArangoClient] = None,
        database: Union[StandardDatabase, str],
        username: str = "root",
        password: str = "",
        auth_method: str = "basic",
    ):
        if isinstance(database, str):
            self._db_name = database
            self.database = None
        else:
            self.database = database

        if not isinstance(database, StandardDatabase):
            self.password = password
            self.username = username
            self.client = client
            self.auth_method = auth_method

    async def initialize(self):
        if self.database is None:
            self.database = await get_or_create_db(
                self.client, self._db_name, user=self.username, password=self.password
            )

    @property
    def initialized(self):
        return isinstance(self.database, StandardDatabase)

    @staticmethod
    async def create_indexes(collection: StandardCollection, model: Type["ArangoModel"]) -> Sequence[Result[Json]]:
        if model.Collection.indexes:
            logger.debug("creating indexes", extra=dict(indexes=model.Collection.indexes, model=model))
        index_requests = []
        for i in model.Collection.indexes or []:
            if isinstance(i, dict):
                index_requests.append(_INDEX_MAPPING[i["type"]](collection, **i))
            else:
                index_requests.append(_INDEX_MAPPING[i.__class__](collection, **dataclasses.asdict(i)))

        return cast(list[Result[Json]], await asyncio.gather(*index_requests))

    async def save(
        self,
        document: "ArangoModel",
        strategy: UpdateStrategy = UpdateStrategy.UPDATE,
        # todo: follow_links: bool = False,
        collection_options: Union[CollectionUpsertOptions, None] = None,
    ) -> Union["ArangoModel", "TVertexModel"]:
        model_fields_mapping = None
        if isinstance(document, VertexModel):
            model_fields_mapping, vertices_ids, edge_ids, query = _build_graph_query(
                document, collection_options=collection_options
            )
        else:
            options = (
                collection_options
                and (collection_options.get(document.Collection.name) or collection_options.get(document.__class__))
                or None
            )

            filter_ = _get_upsert_filter(document)
            query = _make_upsert_query(filter_, document, document, ORMQuery(), strategy, options)

        try:
            cursor = await self.execute(query)
        except AQLQueryExecuteError as e:
            logger.exception(query)
            raise e
        else:
            result = await cursor.next()
        if model_fields_mapping:
            db_traverse(cast(VertexModel, document), set(), result, model_fields_mapping, vertices_ids, edge_ids)
        logger.debug("cursor stats", extra=cursor.statistics())
        return document

    async def get(
        self,
        model: Type["ArangoModel"],
        key: str,
        should_raise: bool = False,
        fetch_edges: Union[set[str], bool] = False,
        # fetch_edges_data: Union[set[str], bool] = False,
        fetch_path: bool = False,
        depth: range = range(1, 1),
        prune: bool = False,
        projection: Optional[Type["ArangoModel"]] = None,
        return_raw: bool = False,
    ) -> Optional[Union["TVertexModel", "ArangoModel"]]:
        collection = model.Collection.name
        _id = f"{collection}/{key}"
        d = Document(_id)
        doc = VariableExpression()
        main_query = ORMQuery().let(doc, d)
        return_: Union[VariableExpression, dict[str, VariableExpression]] = doc
        edges: Sequence[str]
        if fetch_edges:
            if isinstance(fetch_edges, set):
                edges = cast(Sequence[str], tuple(fetch_edges))
            else:
                _edges = []
                for i in model.__relationships__.values():
                    if i.via_model:
                        _edges.append(i.via_model.Collection.name)
                edges = _edges

            v = IteratorExpression("v")
            iterators = [v]
            e = IteratorExpression("e")
            iterators.append(e)

            if fetch_path:
                p = IteratorExpression("p")
                iterators.append(p)
            traversal_result = VariableExpression()

            traversal_iterators: TraverseIterators = cast(TraverseIterators, tuple(iterators))
            traversal = (
                ORMQuery()
                .traverse(traversal_iterators, edges, _id, depth, TraversalDirection.OUTBOUND)
                .return_({"v": iterators[0], "e": iterators[1]})
            )
            main_query.let(traversal_result, traversal)
            return_ = {"doc": doc, "edges": traversal_result}

        main_query.return_(return_)

        cursor = await self.execute(main_query)
        result = await cursor.next()
        if not result or (fetch_edges and not result.get("doc")):
            raise DocumentNotFoundError(_id)

        if issubclass(model, VertexModel):
            result, recursive = graph_to_document(result, model)

        if return_raw:
            return result

        result[PYDANGO_SESSION_KEY] = self
        if result is None and should_raise:
            raise DocumentNotFoundError()

        if projection:
            document = projection.from_orm(result, session=self)
        else:
            document = model.from_orm(result, session=self)

        return document

    async def find(self, model: Type[BaseArangoModel], filters=None, skip=None, limit=None):
        if self.database is None:
            raise SessionNotInitializedError(
                "you should call `await session.initialize()` before using the session or initialize it in the"
                " constructor with `StandardDatabase`"
            )
        collection = _collection_from_model(self.database, model)
        return await collection.find(filters, skip, limit)

    async def execute(self, query: "AQLQuery", **options):
        if self.database is None:
            raise SessionNotInitializedError(
                f"you should call `await {self.initialize.__name__}` before using the session or initialize it in the"
                " constructor with `StandardDatabase`"
            )
        prepared_query = query.prepare()
        logger.debug(
            "executing query", extra={"query": prepared_query.query, "bind_vars": json.dumps(prepared_query.bind_vars)}
        )
        return await self.database.aql.execute(
            prepared_query.query, bind_vars=cast(MutableMapping, prepared_query.bind_vars), **options
        )
