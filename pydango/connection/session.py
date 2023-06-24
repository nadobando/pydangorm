import dataclasses
import logging
from collections import OrderedDict, defaultdict
from itertools import groupby
from typing import Iterator, Optional, Type, Union, cast

from aioarango.collection import StandardCollection
from aioarango.database import StandardDatabase
from indexed import IndexedOrderedDict

from pydango import index
from pydango.connection.utils import get_or_create_collection
from pydango.orm.models import ArangoModel, BaseArangoModel, EdgeModel, VertexModel
from pydango.orm.proxy import LazyProxy
from pydango.orm.query import ORMQuery, for_
from pydango.orm.types import TEdge, TVertexModel
from pydango.query.consts import FROM, TO
from pydango.query.expressions import NEW, IteratorExpression, VariableExpression
from pydango.query.functions import First, Length, Merge, UnionArrays
from pydango.query.operations import RangeExpression

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    pass


# def set_operational_fields(document: BaseArangoModel, result: "AIOArangoResponse"):
#     document.key = result["_key"]
#     document.id = result["_id"]
#     document.rev = result["_rev"]


def _collection_from_model(database: StandardDatabase, model: Type[ArangoModel]) -> StandardCollection:
    return database.collection(model.Collection.name)


def _group_by_relation(
    model: BaseArangoModel,
) -> Iterator[tuple[tuple[Type[VertexModel], Optional[Type[EdgeModel]]], str]]:
    relationships = model.__relationships__
    for m, group in groupby(
        relationships,
        lambda x: (relationships[x].link_model, relationships[x].via_model),
    ):
        for thing in group:
            yield m, thing


class PydangoSession:
    def __init__(self, database: StandardDatabase):
        self.database = database

    @classmethod
    def _build_graph_query(cls, document: VertexModel) -> ORMQuery:
        query = ORMQuery()
        _visited: set[int] = set()
        edge_collections, edge_vertex_index, vertex_collections = cls._build_graph(document, _visited)
        vertex_let_queries: dict[Type[VertexModel], VariableExpression] = {}

        for v in vertex_collections:
            from_var, vertices = cls._build_vertex_query(v, vertex_collections, vertex_let_queries)
            query.let(from_var, vertices)

        main = VariableExpression()
        query.let(main, First(vertex_let_queries[document.__class__]))

        for e, coll in edge_vertex_index.items():
            edge_vars = []
            for (from_model, to_model), instances in coll.items():
                for instance, rels in instances.items():
                    iterator, new_rels, ret = cls._bind_edge(
                        from_model, instance, rels, to_model, vertex_collections, vertex_let_queries
                    )
                    v = VariableExpression()
                    query.let(v, for_(iterator, new_rels).return_(ret))

                    merger = IteratorExpression()
                    edge = VariableExpression()
                    query.let(edge, edge_collections[e][instance])

                    merged = VariableExpression()
                    query.let(
                        merged,
                        for_(merger, RangeExpression(0, Length(edge) - 1)).return_(Merge(edge[merger], v[merger])),
                    )
                    edge_vars.append(merged)
                edges: Union[VariableExpression, list[VariableExpression]]
                if len(edge_vars) > 1:
                    edges = cast(list[VariableExpression], UnionArrays(*edge_vars))
                elif len(edge_vars) == 1:
                    edges = edge_vars[0]
                else:
                    continue

                edge_iter = IteratorExpression()
                query.let(VariableExpression(), for_(edge_iter, edges).insert(edge_iter, e.Collection.name))

        return query.return_(main)

    @classmethod
    def _bind_edge(cls, from_model, instance, rels, to_model, vertex_collections, vertex_let_queries):
        from_ = vertex_collections[from_model].keys().index(instance)
        new_rels = [vertex_collections[to_model].keys().index(x) for x in rels]
        from_var = vertex_let_queries[from_model]
        to_var = vertex_let_queries[to_model]
        iterator = IteratorExpression()
        ret = {FROM: from_var[from_]._id, TO: to_var[iterator]._id}
        return iterator, new_rels, ret

    @classmethod
    def _build_vertex_query(cls, v, vertex_collections, vertex_let_queries):
        i = IteratorExpression()
        from_var = VariableExpression()
        vertex_let_queries[v] = from_var
        vertices = for_(i, in_=list(vertex_collections[v].values())).insert(i, v.Collection.name).return_(NEW())
        return from_var, vertices

    @classmethod
    def _build_graph(cls, document: VertexModel, _visited: set[int]):
        vertex_collections: dict[Type[VertexModel], IndexedOrderedDict[ArangoModel]] = OrderedDict()
        edge_collections: dict[Type[EdgeModel], IndexedOrderedDict[list[TEdge]]] = OrderedDict()
        edge_vertex_index: dict[EdgeModel, dict[tuple[Type[VertexModel], Type[VertexModel]], dict[int, list[int]]]] = (
            defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )

        def _prepare_relation(model, edge_cls, edge_doc, relation_doc, visited):
            if edge_doc:
                edge_collections.setdefault(edge_cls, IndexedOrderedDict()).setdefault(id(model), []).append(
                    edge_doc.save_dict()
                )
            traverse(relation_doc, visited)

            edge_vertex_index[edge_cls][model.__class__, relation_doc.__class__][id(model)].append(id(relation_doc))

        def traverse(model: TVertexModel, visited: set):
            if id(model) in visited:
                return

            if isinstance(model, VertexModel):
                vertex_collections.setdefault(model.__class__, IndexedOrderedDict())[id(model)] = model.save_dict()
                visited.add(id(model))

            models: tuple[Type[VertexModel], Optional[Type[EdgeModel]]]
            for models, field in _group_by_relation(model):
                edge_cls: Optional[Type[EdgeModel]] = models[1]
                relation_doc = getattr(model, field)
                if not relation_doc:
                    continue

                if isinstance(relation_doc, LazyProxy):
                    relation_doc = relation_doc.__instance__

                if isinstance(relation_doc, list):
                    z = zip(relation_doc, model.edges.get(field, []))
                    for vertex_doc, edge_doc in z:
                        _prepare_relation(model, edge_cls, edge_doc, vertex_doc, visited)
                else:
                    edge_doc = model.edges.get(field)
                    _prepare_relation(model, edge_cls, edge_doc, relation_doc, visited)

        traverse(document, _visited)
        return edge_collections, edge_vertex_index, vertex_collections

    async def init(self, model: Type[BaseArangoModel]):
        collection = await get_or_create_collection(self.database, model)
        if model.Collection.indexes:
            logger.debug("creating indexes", extra=dict(indexes=model.Collection.indexes, model=model))
        for i in model.Collection.indexes or []:
            await index.mapping[i.__class__](collection, **dataclasses.asdict(i))

    async def save(self, document: ArangoModel) -> ArangoModel:
        if isinstance(document, VertexModel):
            query = self._build_graph_query(document)
        cursor = await query.execute(self.database)
        result = await cursor.next()
        logger.debug("cursor stats", extra=cursor.statistics())
        return document.__class__.from_orm(result, session=self)

    async def get(self, model: Type[ArangoModel], _id: str, should_raise=False) -> Optional[ArangoModel]:
        collection_name = model.Collection.name
        collection = self.database.collection(collection_name)
        try:
            result = await collection.get(_id)
            # result[DALI_SESSION_KW] = self
            if result is None and should_raise:
                raise DocumentNotFoundError()
            document: ArangoModel = model.from_orm(result, session=self)
            return document
        except DocumentNotFoundError:
            return None

    async def find(self, model: Type[ArangoModel], filters=None, skip=None, limit=None):
        collection = _collection_from_model(self.database, model)
        return await collection.find(filters, skip, limit)
