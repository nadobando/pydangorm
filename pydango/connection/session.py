import ctypes
import dataclasses
import logging
import sys
from collections import OrderedDict, defaultdict
from enum import Enum
from itertools import groupby
from typing import Any, Iterator, Optional, Type, Union, cast

from pydango.orm.relations import LIST_TYPES

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from aioarango.collection import StandardCollection
from aioarango.database import StandardDatabase
from indexed import IndexedOrderedDict

from pydango import index
from pydango.connection.utils import get_or_create_collection
from pydango.orm.consts import EDGES
from pydango.orm.models import ArangoModel, BaseArangoModel, EdgeModel, VertexModel
from pydango.orm.proxy import LazyProxy
from pydango.orm.query import ORMQuery, for_
from pydango.orm.types import TEdge, TVertexModel
from pydango.orm.utils import convert_edge_data_to_valid_kwargs
from pydango.query import AQLQuery
from pydango.query.consts import FROM, KEY, TO
from pydango.query.expressions import NEW, IteratorExpression, VariableExpression
from pydango.query.functions import First, Length, Merge, UnionArrays
from pydango.query.operations import RangeExpression
from pydango.query.options import UpsertOptions

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
    return None


class UpdateStrategy(str, Enum):
    UPDATE = "update"
    REPLACE = "replace"


def _make_upsert_query(
    filter_: Any,
    i: Any,
    model: Union[Type[BaseArangoModel], BaseArangoModel],
    query: AQLQuery,
    strategy: UpdateStrategy,
    options: Union[UpsertOptions, None] = None,
):
    if strategy == strategy.UPDATE:
        query = query.upsert(filter_, i, model.Collection.name, update=i, options=options)
    elif strategy == strategy.REPLACE:
        query = query.upsert(filter_, i, model.Collection.name, replace=i, options=options)
    else:
        raise ValueError(f"strategy must be instance of {UpdateStrategy.__name__}")

    return query


def _get_upsert_filter(
    document: Union[BaseArangoModel, VariableExpression], model: Union[Type[BaseArangoModel], None] = None
):
    if not isinstance(document, BaseArangoModel) and model is not None:
        indexes = model.Collection.indexes
    elif isinstance(document, BaseArangoModel):
        indexes = document.Collection.indexes
    else:
        indexes = tuple()

    # todo: check first by _key or _id

    filter_ = {}
    for model_index in indexes:
        if hasattr(model_index, "unique") and model_index.unique:
            filter_ = {index_field: getattr(document, index_field) for index_field in model_index.fields}

        if isinstance(model_index, dict) and model_index.get("unique"):
            filter_ = {j: getattr(document, j) for j in model_index.get("fields", [])}

    if not filter_:
        key = getattr(document, KEY)
        filter_ = {"_key": key} if key is not None else {}  # noqa: PyProtectedMember

    return filter_


CollectionUpsertOptions: TypeAlias = dict[Union[str, Type[BaseArangoModel]], UpsertOptions]


class PydangoSession:
    def __init__(self, database: StandardDatabase):
        self.database = database

    @classmethod
    def _build_graph_query(
        cls,
        document: VertexModel,
        strategy: UpdateStrategy = UpdateStrategy.UPDATE,
        collection_options: Union[CollectionUpsertOptions, None] = None,
    ) -> ORMQuery:
        query = ORMQuery()
        _visited: set[int] = set()
        edge_collections, edge_vertex_index, vertex_collections, model_field_mapping = cls._build_graph(
            document, _visited
        )
        vertex_let_queries: dict[Type[VertexModel], VariableExpression] = {}
        vertices_ids = {}
        edge_ids = defaultdict(lambda: defaultdict(list))
        for v in vertex_collections:
            vertex_docs = list(vertex_collections[v].values())
            vertices_ids[v] = [id(doc) for doc in vertex_docs]
            from_var, vertex_query = cls._build_vertex_query(v, vertex_docs, strategy)
            vertex_let_queries[v] = from_var

            query.let(from_var, vertex_query)

        main = VariableExpression()
        query.let(main, First(vertex_let_queries[document.__class__]))
        edge_let_queries = {}
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
                    edge_ids[e][instance].extend([id(doc) for doc in edge_collections[e][instance]])

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
                # edge_let_queries[e] = edges
                edge_let_queries[e] = VariableExpression()
                query.let(edge_let_queries[e], cls.build_upsert_query(edge_iter, strategy, e, edges))

        fields = defaultdict(list)

        for vertex_cls, vertex_ids in vertices_ids.items():
            if vertex_cls == document.__class__:
                vertex_ids = vertex_ids[1:]

            for i, v_id in enumerate(vertex_ids):
                obj2 = ctypes.cast(v_id, ctypes.py_object).value
                model_fields = model_field_mapping[v_id].get(vertex_cls, {})
                for j, field in enumerate(model_fields.values()):
                    if vertex_cls == document.__class__:
                        if vertex_cls.__relationships__[field].link_type in LIST_TYPES:
                            fields[field].append(vertex_let_queries[vertex_cls][i + j + 1])
                        else:
                            fields[field] = vertex_let_queries[vertex_cls][i + j + 1]

                    else:
                        if vertex_cls.__relationships__[field].link_type in LIST_TYPES:
                            fields[field].append(vertex_let_queries[vertex_cls][i + j])
                        else:
                            fields[field] = vertex_let_queries[vertex_cls][i + j + 1]
                # todo: handle recursive
                break

            edges = defaultdict(list)
            # edges ={}
            for edge_cls, edge_ids in edge_ids.items():
                for i, e_id in enumerate(edge_ids):
                    obj2 = ctypes.cast(e_id, ctypes.py_object).value
                    model_fields = model_field_mapping[e_id].get(edge_cls, {})
                    for j, field in enumerate(model_fields.values()):
                        # obj2 = ctypes.cast(relation_doc, ctypes.py_object).value
                        var = VariableExpression()
                        query.let(var, edge_let_queries[edge_cls])
                        if vertex_cls.__relationships__[field].link_type in LIST_TYPES:
                            edges[field].append(var[i + j])
                        else:
                            edges[field] = var[i + j]

                    # todo: handle recursive
                    break
                break

        # for vertex_id,v in model_field_mapping.items():
        #     vertices_ids[]
        # pass
        return query.return_(Merge(main, fields, {"edges": edges}))
        # {
        #     "main": main,
        #     "fields":fields,
        #     "vertex": {k.Collection.name: v for k, v in vertex_let_queries.items()},
        #     "edges": {k.Collection.name: v for k, v in edge_let_queries.items()},
        # "edges": edges,
        # }
        # )

    @classmethod
    def _bind_edge(cls, from_model, instance, rels, to_model, vertex_collections, vertex_let_queries):
        from_ = vertex_collections[from_model].keys().index(instance)
        new_rels = [vertex_collections[to_model].keys().index(x) for x in rels]
        from_var = vertex_let_queries[from_model]
        to_var = vertex_let_queries[to_model]
        iterator = IteratorExpression()
        ret = {FROM: from_var[from_]._id, TO: to_var[iterator]._id}  # noqa: PyProtectedMember
        return iterator, new_rels, ret

    @classmethod
    def _build_vertex_query(cls, v, vertices_docs, strategy: UpdateStrategy):
        i = IteratorExpression()
        from_var = VariableExpression()
        query = cls.build_upsert_query(i, strategy, v, vertices_docs)
        return from_var, query

    @classmethod
    def build_upsert_query(
        cls,
        i: IteratorExpression,
        strategy: UpdateStrategy,
        model: Type[BaseArangoModel],
        docs: Union[VariableExpression, list[VariableExpression]],
    ):
        filter_ = _get_upsert_filter(i, model)
        query = for_(i, in_=docs)
        query = _make_upsert_query(filter_, i, model, query, strategy, None).return_(NEW())
        return query

    @classmethod
    def _build_graph(cls, document: VertexModel, _visited: set[int]):
        vertex_collections: dict[Type[VertexModel], IndexedOrderedDict[ArangoModel]] = OrderedDict()
        edge_collections: dict[Type[EdgeModel], IndexedOrderedDict[list[TEdge]]] = OrderedDict()
        edge_vertex_index: dict[
            Type[EdgeModel], dict[tuple[Type[VertexModel], Type[VertexModel]], dict[int, list[int]]]
        ] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        model_fields_mapping: dict[int, defaultdict[str, list[tuple[int, int]]]] = {}

        def _prepare_relation(field, model, edge_cls, edge_doc, relation_doc):
            model_id = id(model)
            if edge_doc:
                edge_collections.setdefault(edge_cls, IndexedOrderedDict()).setdefault(model_id, []).append(edge_doc)

            if model_id not in model_fields_mapping:
                model_fields_mapping[model_id] = {relation_doc.__class__: {}}

            if edge_cls not in model_fields_mapping[model_id]:
                model_fields_mapping[model_id][edge_cls] = {}

            model_fields_mapping[model_id][relation_doc.__class__][id(relation_doc)] = field
            model_fields_mapping[model_id][edge_cls][id(edge_doc)] = field

            edge_vertex_index[edge_cls][model.__class__, relation_doc.__class__][model_id].append(id(relation_doc))

        def traverse(model: TVertexModel, visited: set):
            if id(model) in visited:
                return

            if isinstance(model, VertexModel):
                vertex_collections.setdefault(model.__class__, IndexedOrderedDict())[id(model)] = model
                visited.add(id(model))

            models: tuple[Type[VertexModel], Optional[Type[EdgeModel]]]
            relations = list(_group_by_relation(model))
            if relations:
                for models, field in relations:
                    edge_cls: Optional[Type[EdgeModel]] = models[1]
                    relation_doc = getattr(model, field)
                    if not relation_doc:
                        model_fields_mapping[id(model)] = {}
                        continue

                    if isinstance(relation_doc, LazyProxy):
                        relation_doc = relation_doc.__instance__

                    if model.edges:
                        if isinstance(model.edges, dict):
                            convert_edge_data_to_valid_kwargs(model.edges)
                            model.edges = model.__fields__[EDGES].type_(**model.edges)

                        if isinstance(relation_doc, list):
                            z = zip(relation_doc, getattr(model.edges, field, []))
                            for vertex_doc, edge_doc in z:
                                _prepare_relation(field, model, edge_cls, edge_doc, vertex_doc)
                                traverse(vertex_doc, visited)
                        else:
                            edge_doc = getattr(model.edges, field)
                            _prepare_relation(field, model, edge_cls, edge_doc, relation_doc)
                            traverse(relation_doc, visited)
                    else:
                        # todo: insert join relation
                        pass
            else:
                model_fields_mapping[id(model)] = {}

        traverse(document, _visited)
        return edge_collections, edge_vertex_index, vertex_collections, model_fields_mapping

    async def init(self, model: Type[BaseArangoModel]):
        collection = await get_or_create_collection(self.database, model)
        if model.Collection.indexes:
            logger.debug("creating indexes", extra=dict(indexes=model.Collection.indexes, model=model))
        for i in model.Collection.indexes or []:
            if isinstance(i, dict):
                await index.mapping[i.__class__](collection, **i)
            else:
                await index.mapping[i.__class__](collection, **dataclasses.asdict(i))

    async def save(
        self,
        document: ArangoModel,
        strategy: UpdateStrategy = UpdateStrategy.UPDATE,
        # todo: follow_links: bool = False,
        collection_options: Union[CollectionUpsertOptions, None] = None,
    ) -> ArangoModel:
        if isinstance(document, VertexModel):
            query = self._build_graph_query(document, collection_options=collection_options)
        else:
            options = (
                collection_options
                and (collection_options.get(document.Collection.name) or collection_options.get(document.__class__))
                or None
            )

            filter_ = _get_upsert_filter(document)
            query = _make_upsert_query(filter_, document, document, ORMQuery(), strategy, options)

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
