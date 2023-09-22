import dataclasses
import logging
import sys
from collections import OrderedDict, defaultdict, namedtuple
from enum import Enum
from typing import Any, Iterator, Optional, Type, Union, cast, get_args, get_origin

from aioarango import AQLQueryExecuteError
from pydantic import BaseModel
from pydantic.fields import ModelField

from pydango.connection import DALI_SESSION_KW
from pydango.orm.relations import LIST_TYPES
from pydango.orm.types import ArangoModel, TVertexModel
from pydango.query.utils import new
from pydango.utils import get_collection_from_document

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from aioarango.collection import StandardCollection
from aioarango.database import StandardDatabase
from indexed import IndexedOrderedDict  # type: ignore[attr-defined]

from pydango import index
from pydango.connection.utils import get_or_create_collection
from pydango.orm.consts import EDGES
from pydango.orm.models import BaseArangoModel, EdgeModel, VertexModel
from pydango.orm.proxy import LazyProxy
from pydango.orm.query import ORMQuery, for_
from pydango.orm.utils import convert_edge_data_to_valid_kwargs
from pydango.query import AQLQuery
from pydango.query.consts import FROM, ID, KEY, REV, TO
from pydango.query.expressions import IteratorExpression, VariableExpression
from pydango.query.functions import Document, Length, Merge, UnionArrays
from pydango.query.operations import RangeExpression, TraversalDirection
from pydango.query.options import UpsertOptions

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    pass


# def set_operational_fields(document: BaseArangoModel, result: "AIOArangoResponse"):
#     document.key = result["_key"]
#     document.id = result["_id"]
#     document.rev = result["_rev"]


class MySpecialIter:
    def __init__(self, d):
        self.d = d

    def __iter__(self):
        return iter(self.d)


class groupby:
    # [k for k, g in groupby('AAAABBBCCDAABBB')] --> A B C D A B
    # [list(g) for k, g in groupby('AAAABBBCCD')] --> AAAA BBB CC D

    def __init__(self, iterable, key=None):
        if key is None:

            def key(x):
                return x

        self.keyfunc = key
        self.it = iter(iterable)
        self.tgtkey = self.currkey = self.currvalue = object()

    def __iter__(self):
        return self

    def __next__(self):
        self.id = object()
        while self.currkey == self.tgtkey:
            self.currvalue = next(self.it)  # Exit on StopIteration
            self.currkey = self.keyfunc(self.currvalue)
        self.tgtkey = self.currkey
        return self.currkey, self._grouper(self.tgtkey, self.id)

    def _grouper(self, tgtkey, id):
        while self.id is id and self.currkey == tgtkey:
            yield self.currvalue
            if get_origin(self.currvalue) is Union:
                continue
            try:
                self.currvalue = next(self.it)
            except StopIteration:
                return
            self.currkey = self.keyfunc(self.currvalue)


def _collection_from_model(database: StandardDatabase, model: Type[BaseArangoModel]) -> StandardCollection:
    return database.collection(model.Collection.name)


def _group_by_relation(
    model: BaseArangoModel,
) -> Iterator[tuple[tuple[Type[VertexModel], Optional[Type[EdgeModel]]], str]]:
    relationships = model.__relationships__

    def grouper(x):
        source = relationships[x].link_model
        if source is Union:
            source = get_args(source)

        dst = relationships[x].via_model
        if dst is Union:
            dst = get_args(source)

        return source, dst

    for m, group in groupby(
        relationships,
        lambda x: (relationships[x].link_model, relationships[x].via_model),
    ):
        for thing in group:
            if get_origin(m[0]) is Union:
                for i in get_args(m[0]):
                    yield (i, m[1]), thing
            else:
                yield m, thing
    return None


RelationGroup = namedtuple("RelationGroup", ["collection", "field", "model", "via_model"])


def _group_by_relation2(
    model: BaseArangoModel,
) -> Iterator[RelationGroup]:
    relationships = model.__relationships__
    for field, relation in relationships.items():
        if get_origin(relation.link_model) is Union:
            for model_option in get_args(relation.link_model):
                # model_option: ArangoModel
                yield RelationGroup(model_option.Collection.name, field, model_option, relation.via_model)
                # result[model_option.Collection.name][field][model_option] = relation.via_model
        else:
            yield RelationGroup(relation.link_model.Collection.name, field, relation.link_model, relation.via_model)
            # result[relation.link_model.Collection.name][field][relation.link_model] = relation.via_model


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
    document: Union["BaseArangoModel", VariableExpression], model: Union[Type["BaseArangoModel"], None] = None
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


def _build_upsert_query(
    i: IteratorExpression,
    strategy: UpdateStrategy,
    model: Type["BaseArangoModel"],
    docs: Union[VariableExpression, list[VariableExpression]],
    *,
    edge: bool = False,
):
    filter_ = _get_upsert_filter(i, model)
    query = for_(i, in_=docs)
    query = _make_upsert_query(filter_, i, model, query, strategy, None).return_(new(edge=edge))
    return query


def _build_vertex_query(v, vertices_docs, strategy: UpdateStrategy):
    i = IteratorExpression()
    from_var = VariableExpression(v.Collection.name)
    query = _build_upsert_query(i, strategy, v, vertices_docs)
    return from_var, query


def _bind_edge(from_model, instance, rels, to_model, vertex_collections, vertex_let_queries):
    from_ = vertex_collections[from_model].keys().index(instance)
    new_rels = [vertex_collections[to_model].keys().index(x) for x in rels]
    from_var = vertex_let_queries[from_model]
    to_var = vertex_let_queries[to_model]
    iterator = IteratorExpression()
    ret = {FROM: from_var[from_]._id, TO: to_var[iterator]._id}  # noqa: PyProtectedMember
    return iterator, new_rels, ret


CollectionUpsertOptions: TypeAlias = dict[Union[str, Type["BaseArangoModel"]], UpsertOptions]
ModelFieldMapping: TypeAlias = dict[int, defaultdict[str, list[tuple[int, int]]]]
VerticesIdsMapping: TypeAlias = dict[Type[VertexModel], dict[int, int]]
EdgesIdsMapping: TypeAlias = defaultdict[Type[EdgeModel], defaultdict[int, dict[int, int]]]


def traverse2(
    model: VertexModel,
    visited: set,
    result,
    model_fields_mapping: ModelFieldMapping,
    vertices_ids: VerticesIdsMapping,
    edges_ids: EdgesIdsMapping,
):
    model_id = id(model)
    if model_id in visited:
        return

    if isinstance(model, VertexModel):
        visited.add(model_id)

    v_index = vertices_ids[model.__class__][model_id]
    v_obj = result["vertex"][model.Collection.name][v_index]
    model.id = v_obj[ID]
    model.key = v_obj[KEY]
    model.rev = v_obj[REV]

    models: tuple[Type[VertexModel], Optional[Type[EdgeModel]]]
    relations = list(_group_by_relation(model))
    if relations:
        for models, field in relations:
            relation_doc = getattr(model, field)
            if not relation_doc:
                continue

            if isinstance(relation_doc, LazyProxy):
                relation_doc = relation_doc.__instance__

            if model.edges:
                for edge_field, obj in model.edges.__dict__.items():
                    if isinstance(obj, list):
                        for i in obj:
                            _set_edge_operational_fields(result, model_id, edges_ids, i)
                    elif obj is not None:
                        _set_edge_operational_fields(result, model_id, edges_ids, obj)
                if isinstance(relation_doc, list):
                    z = zip(relation_doc, getattr(model.edges, field, []))
                    for vertex_doc, edge_doc in z:
                        traverse2(vertex_doc, visited, result, model_fields_mapping, vertices_ids, edges_ids)
                else:
                    getattr(model.edges, field)
                    traverse2(relation_doc, visited, result, model_fields_mapping, vertices_ids, edges_ids)
            else:
                # todo: insert join relation
                pass
    else:
        pass
        # model_fields_mapping[id(model)] = {}


def _set_edge_operational_fields(result, model_id, edges_ids, i):
    e_obj = result["edges"][i.Collection.name][edges_ids[i.__class__][model_id][id(i)]]
    i.id = e_obj[ID]
    i.key = e_obj[KEY]
    i.rev = e_obj[REV]
    i.from_ = e_obj[FROM]
    i.to = e_obj[TO]


EdgeCollectionsMapping: TypeAlias = dict[Type[EdgeModel], IndexedOrderedDict[list[EdgeModel]]]
EdgeVerticesIndexMapping = dict[
    Type[EdgeModel], dict[tuple[Type[VertexModel], Type[VertexModel]], dict[int, list[int]]]
]

VertexCollectionsMapping = dict[Type[VertexModel], IndexedOrderedDict[BaseArangoModel]]


class PydangoSession:
    def __init__(self, database: StandardDatabase):
        self.database = database

    @classmethod
    def _build_graph(
        cls, document: VertexModel, _visited: set[int]
    ) -> tuple[EdgeCollectionsMapping, EdgeVerticesIndexMapping, VertexCollectionsMapping, ModelFieldMapping]:
        vertex_collections: VertexCollectionsMapping = OrderedDict()
        edge_collections: EdgeCollectionsMapping = OrderedDict()
        edge_vertex_index: EdgeVerticesIndexMapping = {}  # defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        model_fields_mapping: ModelFieldMapping = {}

        def _prepare_relation(field, model, edge_cls, edge_doc, relation_doc):
            model_id = id(model)
            if id(relation_doc) in (
                edge_vertex_index.setdefault(edge_cls, {})
                .setdefault(model_id, {})
                .setdefault((model.__class__, relation_doc.__class__), [])
            ):
                return False

            if edge_doc:
                edge_collections.setdefault(edge_cls, IndexedOrderedDict()).setdefault(model_id, []).append(edge_doc)

            _add_model_field_to_mapping(model, field, relation_doc, edge_doc)

            (
                edge_vertex_index.setdefault(edge_cls, {})
                .setdefault(model_id, {})
                .setdefault((model.__class__, relation_doc.__class__), [])
                .append(id(relation_doc))
            )

            # edge_vertex_index.setdefault(edge_cls, {}).setdefault((model.__class__, relation_doc.__class__),
            #                                                       {}).setdefault(model_id, set[int]()).add(
            #     id(relation_doc))

        def _add_model_field_to_mapping(model, field, relation_doc, edge_doc):
            model_id = id(model)

            mapping = model_fields_mapping.setdefault(model.__class__, {})
            model_mapping = mapping.setdefault(model_id, {})

            if model.__relationships__[field].link_type in LIST_TYPES:
                model_mapping.setdefault(field, []).append({"v": id(relation_doc), "e": id(edge_doc)})
            else:
                model_mapping[field] = {"v": id(relation_doc), "e": id(edge_doc)}

        def traverse_old(model: VertexModel, visited: set[int]):
            if id(model) in visited:
                return

            if isinstance(model, VertexModel):
                vertex_collections.setdefault(model.__class__, IndexedOrderedDict())[id(model)] = model
                visited.add(id(model))

            models: tuple[Type[VertexModel], Optional[Type[EdgeModel]]]
            relations = list(_group_by_relation2(model))
            if relations:
                for models, field in relations:
                    edge_cls: Optional[Type[EdgeModel]] = models[1]
                    relation_doc: ModelField = getattr(model, field)
                    if not relation_doc:
                        _add_model_field_to_mapping(model, field, None, None)
                        continue

                    if isinstance(relation_doc, LazyProxy):
                        relation_doc = relation_doc.__instance__

                    if model.edges:
                        if isinstance(model.edges, dict):
                            convert_edge_data_to_valid_kwargs(model.edges)
                            # todo: this initiate the class edge model so it validates the edges, should we do that?
                            model.edges = model.__fields__[EDGES].type_(**model.edges)

                        if isinstance(relation_doc, list):
                            if len(getattr(model.edges, field, [])) != len(relation_doc):
                                raise AssertionError(f"{model.__class__.__name__} vertex edges {field} number mismatch")
                            z = zip(relation_doc, getattr(model.edges, field, []))
                            for vertex_doc, edge_doc in z:
                                _prepare_relation(field, model, edge_cls, edge_doc, vertex_doc)
                                traverse_old(vertex_doc, visited)
                        else:
                            edge_doc = getattr(model.edges, field)
                            _prepare_relation(field, model, edge_cls, edge_doc, relation_doc)
                            traverse_old(relation_doc, visited)
                    else:
                        # todo: insert join relation
                        pass
            else:
                pass
                # model_fields_mapping[id(model)] = {}

        def traverse_new(model: VertexModel, visited: set[int]):
            nonlocal edge_collections
            if id(model) in visited:
                return

            if isinstance(model, VertexModel):
                vertex_collections.setdefault(model.__class__, IndexedOrderedDict())[id(model)] = model
                visited.add(id(model))

            relations = list(_group_by_relation2(model))
            if relations:
                for relation_group in relations:
                    relation_doc: VertexModel = getattr(model, relation_group.field)
                    if not relation_doc:
                        _add_model_field_to_mapping(model, relation_group.field, None, None)
                        continue

                    edge_cls: Optional[Type[EdgeModel]] = relation_group.via_model

                    if isinstance(relation_doc, LazyProxy):
                        relation_doc = relation_doc.__instance__

                    if model.edges:
                        if isinstance(model.edges, dict):
                            convert_edge_data_to_valid_kwargs(model.edges)
                            # todo: this initiate the class edge model so it validates the edges, should we do that?
                            model.edges = model.__fields__[EDGES].type_(**model.edges)

                        if isinstance(relation_doc, list):
                            if len(getattr(model.edges, relation_group.field, [])) != len(relation_doc):
                                raise AssertionError(
                                    f"{model.__class__.__name__} vertex edges {relation_group.field} number mismatch"
                                )
                            z = zip(relation_doc, getattr(model.edges, relation_group.field, []))
                            for vertex_doc, edge_doc in z:
                                _prepare_relation(relation_group.field, model, edge_cls, edge_doc, vertex_doc)
                                traverse_new(vertex_doc, visited)

                        else:
                            edge_doc = getattr(model.edges, relation_group.field)
                            _prepare_relation(relation_group.field, model, edge_cls, edge_doc, relation_doc)
                            traverse_new(relation_doc, visited)
                    else:
                        # todo: insert join relation
                        pass
            else:
                pass
                # model_fields_mapping[id(model)] = {}

        traverse_new(document, _visited)
        return edge_collections, edge_vertex_index, vertex_collections, model_fields_mapping

    @classmethod
    def _build_graph_query(
        cls,
        document: VertexModel,
        strategy: UpdateStrategy = UpdateStrategy.UPDATE,
        collection_options: Union[CollectionUpsertOptions, None] = None,
    ) -> tuple[ModelFieldMapping, VerticesIdsMapping, EdgesIdsMapping, ORMQuery]:
        query = ORMQuery()
        _visited: set[int] = set()
        edge_collections, edge_vertex_index, vertex_collections, model_fields_mapping = cls._build_graph(
            document, _visited
        )
        vertex_let_queries: dict[Type[VertexModel], VariableExpression] = {}
        vertices_ids: VerticesIdsMapping = {}
        edge_ids: EdgesIdsMapping = {}
        for v in vertex_collections:
            vertex_docs = list(vertex_collections[v].values())
            vertices_ids[v] = {id(doc): i for i, doc in enumerate(vertex_docs)}
            from_var, vertex_query = _build_vertex_query(v, vertex_docs, strategy)
            vertex_let_queries[v] = from_var

            query.let(from_var, vertex_query)

        edge_let_queries = {}

        def invert_edge_index(d: dict):
            r = {}
            for k, v in d.items():
                for nested_key, nested_value in v.items():
                    r.setdefault(nested_key, {})[k] = nested_value
            return r

        for e, coll in edge_vertex_index.items():
            counter = 0
            edge_vars = []
            for j, (instance, mapping) in enumerate(list(coll.items())):
                iterator = IteratorExpression()
                edge_ids.setdefault(e, {}).setdefault(instance, {}).update(
                    {id(doc): i + counter for i, doc in enumerate(edge_collections[e][instance])}
                )
                edge_var_name = f"{e.Collection.name}_{j + 1}"
                edge = VariableExpression(edge_var_name)
                query.let(edge, edge_collections[e][instance])
                for k, ((from_model, to_model), rels) in enumerate(mapping.items()):
                    from_ = vertex_collections[from_model].keys().index(instance)
                    new_rels = [vertex_collections[to_model].keys().index(x) for x in rels]
                    from_var = vertex_let_queries[from_model]
                    to_var = vertex_let_queries[to_model]
                    ret = {FROM: from_var[from_]._id, TO: to_var[iterator]._id}

                    edge_from_to = VariableExpression(edge_var_name + f"_{k}_from_to")
                    query.let(edge_from_to, for_(iterator, new_rels).return_(ret))

                    merger = IteratorExpression("merger")

                    merged = VariableExpression(edge_var_name + f"_{k}_merged")
                    query.let(
                        merged,
                        for_(merger, RangeExpression(0, Length(edge_from_to) - 1)).return_(
                            Merge(edge[merger], edge_from_to[merger])
                        ),
                    )
                    edge_vars.append(merged)
                    counter += len(rels)

            edges: Union[VariableExpression, list[VariableExpression]]
            if len(edge_vars) > 1:
                edges = cast(list[VariableExpression], UnionArrays(*edge_vars))
            elif len(edge_vars) == 1:
                edges = edge_vars[0]
            else:
                continue

            edge_iter = IteratorExpression()
            edge_let_queries[e] = VariableExpression(edge_var_name + "_result")
            query.let(edge_let_queries[e], _build_upsert_query(edge_iter, strategy, e, edges, edge=True))

        return (
            model_fields_mapping,
            vertices_ids,
            edge_ids,
            query.return_(
                {
                    "vertex": {k.Collection.name: v for k, v in vertex_let_queries.items()},
                    "edges": {k.Collection.name: v for k, v in edge_let_queries.items()},
                }
            ),
        )

    async def init(self, model: Type[BaseArangoModel]):
        collection = await get_or_create_collection(self.database, model)
        await self.create_indexes(collection, model)

    @staticmethod
    async def create_indexes(collection, model):
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
    ) -> Union[ArangoModel, TVertexModel]:
        model_fields_mapping = None
        if isinstance(document, VertexModel):
            model_fields_mapping, vertices_ids, edge_ids, query = self._build_graph_query(
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
            cursor = await query.execute(self.database)
        except AQLQueryExecuteError as e:
            logger.exception(query)
            raise e
        else:
            result = await cursor.next()
        if model_fields_mapping:
            traverse2(cast(VertexModel, document), set(), result, model_fields_mapping, vertices_ids, edge_ids)
        logger.debug("cursor stats", extra=cursor.statistics())
        return document

    async def get(
        self,
        model: Type[BaseArangoModel],
        key: str,
        should_raise: bool = False,
        fetch_edges: Union[set[str], bool] = False,
        fetch_edges_data: Union[set[str], bool] = False,
        fetch_path: bool = False,
        depth: range = range(1, 1),
        prune: bool = False,
        projection: Optional[Type[BaseArangoModel]] = None,
        return_raw: bool = False,
    ) -> Optional[Union[TVertexModel, ArangoModel]]:
        collection = model.Collection.name
        _id = f"{collection}/{key}"
        d = Document(_id)
        doc = VariableExpression()
        main_query = ORMQuery().let(doc, d)
        return_ = doc
        if fetch_edges:
            if isinstance(fetch_edges, set):
                edges = fetch_edges
            else:
                edges = tuple({i.via_model.Collection.name for i in model.__relationships__.values()})

            v = IteratorExpression("v")
            iterators = [v]
            e = IteratorExpression("e")
            iterators.append(e)
            # if fetch_edges_data:

            if fetch_path:
                p = IteratorExpression("p")
                iterators.append(p)
            traversal_result = VariableExpression()
            traversal = (
                ORMQuery()
                .traverse(tuple(iterators), edges, _id, depth, TraversalDirection.OUTBOUND)
                .return_({"v": iterators[0], "e": iterators[1]})
            )
            main_query.let(traversal_result, traversal)
            return_ = {"doc": return_, "edges": traversal_result}

        main_query.return_(return_)
        # logger.debug(str(main_query))
        cursor = await main_query.execute(self.database)
        result = await cursor.next()
        result, recursive = construct(result, model)

        if return_raw:
            return result

        result[DALI_SESSION_KW] = self
        if result is None and should_raise:
            raise DocumentNotFoundError()

        if projection:
            document = projection.from_orm(result, session=self)
        else:
            document = model.from_orm(result, session=self)

        return document

    # except DocumentNotFoundError:
    #     return None

    async def find(self, model: Type[BaseArangoModel], filters=None, skip=None, limit=None):
        collection = _collection_from_model(self.database, model)
        return await collection.find(filters, skip, limit)


def traverse_model_and_map(pydantic_model: Type[BaseModel], variable: VariableExpression):
    result = {}

    for field, value in pydantic_model.__fields__.items():
        if value.alias:
            field = value.alias
        if issubclass(value.type_, BaseModel):
            result[field] = traverse_model_and_map(value.type_, variable)
        elif isinstance(value.type_, list):
            result[field] = []
            for item in value.type_:
                if issubclass(item, BaseModel):
                    result[field].append(traverse_model_and_map(item, variable))
                elif isinstance(item, dict):
                    mapped_item = {}
                    for key, val in item.items():
                        mapped_item[key] = variable[val]
                    result[field].append(mapped_item)
        elif isinstance(value.type_, dict):
            mapped_value = {}
            for key, val in value.type_.items():
                mapped_value[key] = variable[val]
            result[field] = mapped_value
        else:
            result[field] = variable[field]

    return result


def construct(traversal_result: dict, model: Type[VertexModel]):
    doc = traversal_result["doc"]

    # for relation in traversal_result["edges"]:
    #     v = relation["v"]
    #     e = relation["e"]
    #     coll, _, __ = e[ID].partition("/")
    #     for func in model.__edge_to_field_mapping__[coll]:
    #         if func(e, v):
    #             link_type = model.__relationships__[func.__name__].link_type
    #             if link_type in LIST_TYPES:
    #                 if func.__name__ not in new_d:
    #                     new_d[func.__name__] = []
    #                 new_d[func.__name__].append(v)
    #                 if func.__name__ not in new_d[EDGES]:
    #                     new_d[EDGES][func.__name__] = []
    #                 new_d[EDGES][func.__name__].append(e)
    #             else:
    #                 new_d[func.__name__] = v
    #                 new_d[EDGES][func.__name__] = e
    #             break

    vertices = defaultdict(dict)
    edges = {}
    if doc:
        vertices[doc[ID]] = doc
    edge_count = 0
    for relation in traversal_result["edges"]:
        v = relation["v"]
        e = relation["e"]
        edge_coll = get_collection_from_document(e)
        vertices[v[ID]] = v
        coordinate = (e[FROM], e[TO])

        if coordinate not in edges:
            edges.setdefault(edge_coll, {})[coordinate] = e

        elif not isinstance(edges[coordinate], list):
            edges.setdefault(edge_coll, {})[coordinate] = [edges[coordinate]]
            edges[edge_coll][coordinate].append(e)

        else:
            edges[edge_coll][coordinate].append(e)

        edge_count += 1
    if len(traversal_result["edges"]) != edge_count:
        raise AssertionError("something happend edges are not the same length")

    new_d, recursive = reorder_graph({"start": doc[ID], "vertices": vertices, "edges": edges}, model)

    return new_d, recursive


def reorder_graph(graph, model):
    vertices = graph["vertices"]
    edges = graph["edges"]
    start = graph["start"]
    visited = set()
    recursive = False
    for coll, _edges in edges.items():
        for (f, t), e in _edges.items():
            to = vertices[t]
            coll, _, __ = e[ID].partition("/")

            for func in model.__edge_to_field_mapping__[coll]:
                if to[ID] == start:
                    continue
                if callable(func):
                    if func(e, to):
                        map_edge(e, f, func.__name__, model, to, vertices)
                        break
                else:
                    map_edge(e, f, func, model, to, vertices)

                if id(to) in visited:
                    recursive = True
                visited.add(id(to))

    return vertices[start], recursive


def map_edge(e, f, func, model, to, vertices):
    link_type = model.__relationships__[func].link_type
    if link_type in LIST_TYPES:
        if func not in vertices[f]:
            vertices[f][func] = []

        vertices[f][func].append(to)

        if func not in vertices[f].setdefault(EDGES, {}):
            vertices[f][EDGES][func] = []
        vertices[f][EDGES][func].append(e)
    else:
        vertices[f][func] = to
        vertices[f].setdefault(EDGES, {})[func] = e


def remove_circular_refs(ob, _seen=None):
    if _seen is None:
        _seen = set()
    if id(ob) in _seen:
        return None
    _seen.add(id(ob))
    res = ob
    if isinstance(ob, dict):
        res = {remove_circular_refs(k, _seen): remove_circular_refs(v, _seen) for k, v in ob.items()}
    elif isinstance(ob, (list, tuple, set, frozenset)):
        objs = type(ob)(remove_circular_refs(v, _seen) for v in ob)
        res = all(objs) and objs or None

    _seen.remove(id(ob))
    return res
