from typing import TYPE_CHECKING

from pydango.orm.models.fields import ModelFieldExpression

if TYPE_CHECKING:
    from pydango.orm.models.base import ArangoModel


def save_dict(model: "ArangoModel"):
    return model.save_dict()


def convert_edge_data_to_valid_kwargs(edge_dict):
    for i in edge_dict.copy():
        if isinstance(i, ModelFieldExpression):
            edge_dict[i.field] = edge_dict.pop(i)
