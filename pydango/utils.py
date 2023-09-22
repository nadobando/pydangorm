from typing import Union

from pydango.orm.models import BaseArangoModel
from pydango.orm.types import ArangoModel
from pydango.query.consts import ID


def get_collection_from_document(obj: Union[str, dict, ArangoModel]) -> str:
    if isinstance(obj, dict):
        obj = obj.get(ID)
    elif isinstance(obj, BaseArangoModel):
        obj = obj.id

    if not isinstance(obj, str):
        raise ValueError("o")

    return obj.partition("/")[0]
