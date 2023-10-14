from typing import Optional, Sequence, Union

from aioarango import ArangoClient, HTTPClient
from aioarango.connection import (
    BasicConnection,
    Connection,
    JwtConnection,
    JwtSuperuserConnection,
)


def make_connection(  # nosec: B107
    hosts: Union[str, Sequence[str]] = "http://127.0.0.1:8529",
    host_resolver: str = "roundrobin",
    http_client: Optional[HTTPClient] = None,
    db_name: str = "_system",
    username: str = "root",
    password: str = "",
    auth_method: str = "basic",
    superuser_token: Optional[str] = None,
) -> Connection:
    client = ArangoClient(hosts, host_resolver, http_client)

    if superuser_token is not None:
        return JwtSuperuserConnection(
            hosts=client.hosts,
            host_resolver=client._host_resolver,
            sessions=client._sessions,
            db_name=db_name,
            http_client=client._http,
            serializer=client._serializer,
            deserializer=client._deserializer,
            superuser_token=superuser_token,
        )

    elif auth_method.lower() == "basic":
        return BasicConnection(
            hosts=client.hosts,
            host_resolver=client._host_resolver,
            sessions=client._sessions,
            db_name=db_name,
            username=username,
            password=password,
            http_client=client._http,
            serializer=client._serializer,
            deserializer=client._deserializer,
        )
    elif auth_method.lower() == "jwt":
        return JwtConnection(
            hosts=client.hosts,
            host_resolver=client._host_resolver,
            sessions=client._sessions,
            db_name=db_name,
            username=username,
            password=password,
            http_client=client._http,
            serializer=client._serializer,
            deserializer=client._deserializer,
        )

    else:
        raise ValueError(f"invalid auth_method: {auth_method}")
