from functools import partial
from typing import TYPE_CHECKING, Generic

from pydango import NAO
from pydango.orm.encoders import jsonable_encoder
from pydango.orm.types import ArangoModel
from pydango.query.expressions import ObjectExpression

if TYPE_CHECKING:
    from pydango.connection.session import PydangoSession


class LazyProxyMeta(type):
    def __new__(cls, name, bases, namespace, **kwargs):
        return super().__new__(cls, name, bases, namespace, **kwargs)


class LazyProxy(Generic[ArangoModel], metaclass=LazyProxyMeta):
    _initialized: bool = False
    __instance__ = None

    def __init__(self, instance, field, session: "PydangoSession"):
        self.session = session
        self._field = field
        if instance is not NAO:
            self._initialized = True

        self.__instance__ = instance

    def __getattr__(self, item):
        if item in getattr(self, "__dict__"):
            return getattr(self, item)

        if isinstance(self.__instance__, list):
            if item in ["dict"]:
                return partial(jsonable_encoder, obj=self.__instance__)

            # if item in getattr(getattr(self, '_instance'), item):
        attr = getattr(self.__instance__, item, None)
        if attr:
            return attr
        else:
            return getattr(self._field.type_, item)

    def __repr__(self):
        return repr(self.__instance__)

    def __getitem__(self, item):
        if self:
            return self.__instance__[item]
        raise AttributeError(
            "you are attempting to access "
            f"{self._field.type_.__name__} via {self._field.name} which is not initialized use fetch"
        )

    def __bool__(self):
        return self._initialized and bool(self.__instance__)

    def fetch(self):
        self.session.get(
            self._field.type_,
        )

    def compile(self, query_ref):
        return ObjectExpression(self.dict()).compile(query_ref)

    def dict(self, *args, by_alias=True, **kwargs):
        return jsonable_encoder(self.__instance__, by_alias=by_alias, *args, **kwargs)
