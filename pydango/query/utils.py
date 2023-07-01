from typing import Protocol, TypeVar, Union

from pydango.query.consts import FROM, ID, KEY, REV, TO
from pydango.query.expressions import NEW


class Compilable(Protocol):
    def compile(self, *args, **kwargs) -> Union[str, None]:
        ...


T = TypeVar("T")


def new(*, edge=False) -> dict[str, str]:
    _new = NEW()
    d = {ID: _new[ID], KEY: _new[KEY], REV: _new[REV]}
    if edge:
        d.update({FROM: _new[FROM], TO: _new[TO]})
    return d
