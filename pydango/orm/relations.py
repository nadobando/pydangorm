from enum import Enum


class LinkTypes(str, Enum):
    DIRECT = "DIRECT"
    OPTIONAL_DIRECT = "OPTIONAL_DIRECT"
    LIST = "LIST"
    OPTIONAL_LIST = "OPTIONAL_LIST"
    EDGE = "EDGE"
    OPTIONAL_EDGE = "OPTIONAL_EDGE"
    EDGE_LIST = "EDGE_LIST"
    OPTIONAL_EDGE_LIST = "OPTIONAL_EDGE_LIST"


EDGE_TYPES = (
    LinkTypes.EDGE,
    LinkTypes.OPTIONAL_EDGE,
    LinkTypes.OPTIONAL_EDGE_LIST,
    LinkTypes.EDGE_LIST,
)

LIST_TYPES = (
    LinkTypes.EDGE_LIST,
    LinkTypes.OPTIONAL_EDGE_LIST,
    LinkTypes.LIST,
    LinkTypes.OPTIONAL_LIST,
)

SINGLETON_TYPES = (
    LinkTypes.EDGE,
    LinkTypes.DIRECT,
    LinkTypes.OPTIONAL_EDGE,
    LinkTypes.OPTIONAL_DIRECT,
)
