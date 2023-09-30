from typing import TYPE_CHECKING, Any, Type, Union, cast

from pydango.connection.graph_utils import (
    EdgesIdsMapping,
    ModelFieldMapping,
    VerticesIdsMapping,
    _build_graph,
)
from pydango.connection.types import CollectionUpsertOptions, UpdateStrategy
from pydango.orm import ORMQuery
from pydango.orm.models import BaseArangoModel
from pydango.orm.query import for_
from pydango.query.consts import FROM, KEY, TO
from pydango.query.expressions import (
    IteratorExpression,
    RangeExpression,
    VariableExpression,
)
from pydango.query.functions import Length, Merge, UnionArrays
from pydango.query.options import UpsertOptions
from pydango.query.utils import new

if TYPE_CHECKING:
    from pydango.orm import VertexModel
    from pydango.query import AQLQuery


def _make_upsert_query(
    filter_: Any,
    i: Any,
    model: Union[Type[BaseArangoModel], BaseArangoModel],
    query: "AQLQuery",
    strategy: UpdateStrategy,
    options: Union[UpsertOptions, None] = None,
):
    if strategy == strategy.UPDATE:
        query = query.upsert(filter_, i, model.Collection.name, update=i, options=options)
    elif strategy == strategy.REPLACE:
        query = query.upsert(filter_, i, model.Collection.name, replace=i, options=options)

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


def _build_graph_query(
    document: "VertexModel",
    strategy: UpdateStrategy = UpdateStrategy.UPDATE,
    collection_options: Union[CollectionUpsertOptions, None] = None,
) -> tuple[ModelFieldMapping, VerticesIdsMapping, EdgesIdsMapping, ORMQuery]:
    query = ORMQuery()
    _visited: set[int] = set()
    edge_collections, edge_vertex_index, vertex_collections, model_fields_mapping = _build_graph(document, _visited)
    vertex_let_queries: dict[Type["VertexModel"], VariableExpression] = {}
    vertices_ids: VerticesIdsMapping = {}
    edge_ids: EdgesIdsMapping = {}
    for v in vertex_collections:
        vertex_docs = list(vertex_collections[v].values())
        vertices_ids[v] = {id(doc): i for i, doc in enumerate(vertex_docs)}
        from_var, vertex_query = _build_vertex_query(v, vertex_docs, strategy)
        vertex_let_queries[v] = from_var

        query.let(from_var, vertex_query)

    edge_let_queries = {}

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
            from_model: Type["VertexModel"]
            to_model: Type["VertexModel"]
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
