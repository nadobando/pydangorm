from aioarango.connection import (
    BasicConnection as BasicConnection,
    Connection as Connection,
    JwtConnection as JwtConnection,
    JwtSuperuserConnection as JwtSuperuserConnection,
)
from aioarango.database import StandardDatabase as StandardDatabase
from aioarango.exceptions import ServerConnectionError as ServerConnectionError
from aioarango.http import DefaultHTTPClient as DefaultHTTPClient, HTTPClient as HTTPClient
from aioarango.resolver import (
    HostResolver as HostResolver,
    RandomHostResolver as RandomHostResolver,
    RoundRobinHostResolver as RoundRobinHostResolver,
    SingleHostResolver as SingleHostResolver,
)
from typing import Any, Callable, Optional, Sequence, Union

class ArangoClient:
    def __init__(
        self,
        hosts: Union[str, Sequence[str]] = ...,
        host_resolver: str = ...,
        http_client: Optional[HTTPClient] = ...,
        serializer: Callable[..., str] = ...,
        deserializer: Callable[[str], Any] = ...,
    ) -> None: ...
    async def close(self) -> None: ...
    @property
    def hosts(self) -> Sequence[str]: ...
    @property
    def version(self): ...
    async def db(
        self,
        name: str = ...,
        username: str = ...,
        password: str = ...,
        verify: bool = ...,
        auth_method: str = ...,
        superuser_token: Optional[str] = ...,
    ) -> StandardDatabase: ...
