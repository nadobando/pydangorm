from collections import OrderedDict, defaultdict
from typing import (
    Any,
    DefaultDict,
    Iterator,
    Optional,
    Type,
    Union,
    cast,
    get_args,
    get_origin,
)

from indexed import IndexedOrderedDict

from pydango.connection.types import (
    EdgeCollectionsMapping,
    EdgesIdsMapping,
    EdgeVerticesIndexMapping,
    ModelFieldMapping,
    RelationGroup,
    VertexCollectionsMapping,
    VerticesIdsMapping,
)
from pydango.orm.consts import EDGES
from pydango.orm.models import EdgeModel, VertexModel
from pydango.orm.models.base import LIST_TYPES, ArangoModel, BaseArangoModel, LazyProxy
from pydango.orm.models.utils import convert_edge_data_to_valid_kwargs
from pydango.orm.models.vertex import TVertexModel
from pydango.query.consts import FROM, ID, KEY, REV, TO


def get_collection_from_document(obj: Union[str, dict, "ArangoModel"]) -> str:
    _obj = None
    if isinstance(obj, dict):
        _obj = obj.get(ID)
    elif isinstance(obj, BaseArangoModel):
        _obj = obj.id

    if not _obj or not isinstance(_obj, str):
        raise ValueError("cannot parse collection")

    return _obj.partition("/")[0]


def _group_by_relation(
    model: BaseArangoModel,
) -> Iterator[RelationGroup]:
    relationships = model.__relationships__
    for field, relation in relationships.items():
        if get_origin(relation.link_model) is Union:
            for model_option in get_args(relation.link_model):
                yield RelationGroup(model_option.Collection.name, field, model_option, relation.via_model)
        else:
            yield RelationGroup(relation.link_model.Collection.name, field, relation.link_model, relation.via_model)


def _set_edge_operational_fields(result, model_id, edges_ids, i):
    e_obj = result["edges"][i.Collection.name][edges_ids[i.__class__][model_id][id(i)]]
    i.id = e_obj[ID]
    i.key = e_obj[KEY]
    i.rev = e_obj[REV]
    i.from_ = e_obj[FROM]
    i.to = e_obj[TO]


def db_traverse(
    model: TVertexModel,
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

    relations = list(_group_by_relation(model))
    if not relations:
        return

    for relation_group in relations:
        relation_doc: Union[TVertexModel, None] = getattr(model, relation_group.field)
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
                z = zip(relation_doc, getattr(model.edges, relation_group.field, []))
                for vertex_doc, edge_doc in z:
                    db_traverse(vertex_doc, visited, result, model_fields_mapping, vertices_ids, edges_ids)
            else:
                getattr(model.edges, relation_group.field)
                db_traverse(
                    cast(VertexModel, relation_doc), visited, result, model_fields_mapping, vertices_ids, edges_ids
                )
        else:
            # todo: insert join relation
            raise NotImplementedError("join relation not implemented yet")


def graph_to_document(traversal_result: dict, model: Type[VertexModel]):
    doc = traversal_result["doc"]

    vertices: DefaultDict[str, dict[str, Any]] = defaultdict(dict)
    edges: dict[str, dict[tuple[str, str], Union[list[dict[str, Any]], dict[str, Any]]]] = {}
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
        elif isinstance(edges[edge_coll][coordinate], list):
            cast(list, edges[edge_coll][coordinate]).append(e)
        else:
            edges.setdefault(edge_coll, {})[coordinate] = [cast(dict[str, Any], edges[edge_coll][coordinate])]
            cast(list, edges[edge_coll][coordinate]).append(e)

        edge_count += 1

    if len(traversal_result["edges"]) != edge_count:
        raise AssertionError("something happened could not map all edges")

    new_d, recursive = map_graph_edges({"start": doc[ID], "vertices": vertices, "edges": edges}, model)

    return new_d, recursive


def map_graph_edges(graph, model):
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
    # note here to detect circular references
    #  - not supported in pydantic v1 start in pydantic v2
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


def _build_object_graph_mappings(
    model: "TVertexModel",
    visited: set[int],
    vertex_collections: VertexCollectionsMapping,
    edge_collections: EdgeCollectionsMapping,
    edge_vertex_index: EdgeVerticesIndexMapping,
    model_fields_mapping: ModelFieldMapping,
) -> None:
    def _add_model_field_to_mapping(model, field, relation_doc, edge_doc):
        model_id = id(model)

        mapping = model_fields_mapping.setdefault(model.__class__, {})
        model_mapping = mapping.setdefault(model_id, {})

        if model.__relationships__[field].link_type in LIST_TYPES:
            model_mapping.setdefault(field, []).append({"v": id(relation_doc), "e": id(edge_doc)})
        else:
            model_mapping[field] = {"v": id(relation_doc), "e": id(edge_doc)}

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

    if id(model) in visited:
        return

    if isinstance(model, VertexModel):
        vertex_collections.setdefault(model.__class__, IndexedOrderedDict())[id(model)] = model
        visited.add(id(model))

    relations = list(_group_by_relation(model))

    if not relations:
        return

    for relation_group in relations:
        relation_doc: Union[TVertexModel, None] = getattr(model, relation_group.field)

        if isinstance(relation_doc, LazyProxy):
            relation_doc = cast(VertexModel, relation_doc.__instance__)

        if not relation_doc:
            _add_model_field_to_mapping(model, relation_group.field, None, None)
            continue

        edge_cls: Optional[Type[EdgeModel]] = relation_group.via_model

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
                vertex_doc: VertexModel
                edge_doc: EdgeModel
                for vertex_doc, edge_doc in zip(relation_doc, getattr(model.edges, relation_group.field, [])):
                    _prepare_relation(relation_group.field, model, edge_cls, edge_doc, vertex_doc)
                    _build_object_graph_mappings(
                        vertex_doc,
                        visited,
                        vertex_collections,
                        edge_collections,
                        edge_vertex_index,
                        model_fields_mapping,
                    )

            else:
                edge_doc = getattr(model.edges, relation_group.field)
                _prepare_relation(relation_group.field, model, edge_cls, edge_doc, relation_doc)
                _build_object_graph_mappings(
                    relation_doc, visited, vertex_collections, edge_collections, edge_vertex_index, model_fields_mapping
                )
        else:
            # todo: insert join relation
            pass


def _build_graph(
    document: VertexModel, _visited: set[int]
) -> tuple[EdgeCollectionsMapping, EdgeVerticesIndexMapping, VertexCollectionsMapping, ModelFieldMapping]:
    vertex_collections: VertexCollectionsMapping = OrderedDict()
    edge_collections: EdgeCollectionsMapping = OrderedDict()
    edge_vertex_index: EdgeVerticesIndexMapping = {}  # defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    model_fields_mapping: ModelFieldMapping = {}

    _build_object_graph_mappings(
        document, _visited, vertex_collections, edge_collections, edge_vertex_index, model_fields_mapping
    )
    return edge_collections, edge_vertex_index, vertex_collections, model_fields_mapping
