import sys
from typing import ForwardRef, Union

from pydango.orm.models.fields import RelationModelField
from pydango.orm.models.relations import Relationship

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

RelationshipFields: TypeAlias = dict[str, RelationModelField]
Relationships: TypeAlias = dict[str, Relationship]
EdgeFieldMapping: TypeAlias = dict[Union[str, ForwardRef], list[str]]
