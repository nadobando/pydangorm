from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from pydango.orm.models import BaseArangoModel, EdgeModel, VertexModel  # noqa: F401

ArangoModel = TypeVar("ArangoModel", bound="BaseArangoModel")
TEdge = TypeVar("TEdge", bound="EdgeModel")
TVertexModel = TypeVar("TVertexModel", bound="VertexModel")
