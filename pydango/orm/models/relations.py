from typing import TYPE_CHECKING, ForwardRef, Optional, Type

if TYPE_CHECKING:
    from pydantic.fields import ModelField
    from pydantic.typing import ReprArgs

    from pydango.orm.models.base import LinkTypes
    from pydango.orm.models.edge import TEdge
    from pydango.orm.models.vertex import TVertexModel


class Relationship:
    def __init__(
        self,
        *,
        field: "ModelField",
        back_populates: Optional[str] = None,
        link_model: Type["TVertexModel"],
        via_model: Optional[Type["TEdge"]] = None,
        link_type: "LinkTypes",
    ):
        self.via_model = via_model
        self.link_type = link_type
        self.field = field
        self.link_model = link_model
        self.back_populates = back_populates

    def __repr_args__(self) -> "ReprArgs":
        name = self.link_model.__name__ if not isinstance(self.link_model, ForwardRef) else self.link_model
        args = [("link_model", name), ("link_type", self.link_type.value)]
        if self.via_model:
            args.append(("via_model", self.via_model.__name__))
        return args
