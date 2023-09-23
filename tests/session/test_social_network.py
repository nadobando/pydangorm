import asyncio
import datetime
from typing import Annotated, Any, Iterable, List, Optional, Type, Union

import pytest
from _pytest.fixtures import FixtureRequest
from pydiction import ANY_NOT_NONE, Contains, Matcher

from pydango.connection.session import PydangoSession
from pydango.orm.models import (
    BaseArangoModel,
    EdgeCollectionConfig,
    EdgeModel,
    Relation,
    VertexCollectionConfig,
    VertexModel,
)


class Post(VertexModel):
    title: str
    content: str
    # todo: make this work
    # author: Annotated["User", BackRelation["Authorship"]]
    comments: Annotated[Optional[List["Comment"]], Relation["Commentary"]] = None

    class Collection(VertexCollectionConfig):
        name = "posts"


class Comment(VertexModel):
    text: str

    class Collection(VertexCollectionConfig):
        name = "comments"


class User(VertexModel):
    name: str
    email: str
    age: int
    friends: Annotated[Optional[List["User"]], Relation["Friendship"]] = None
    posts: Annotated[Optional[List["Post"]], Relation["Authorship"]] = None
    comments: Annotated[Optional[List["Comment"]], Relation["Commentary"]]
    likes: Annotated[Optional[List[Union["Post", "Comment"]]], Relation["Like"]] = None

    class Collection(VertexCollectionConfig):
        name = "users"


class Friendship(EdgeModel):
    since: datetime.date

    class Collection(EdgeCollectionConfig):
        name = "friendships"


class Authorship(EdgeModel):
    created_at: datetime.datetime

    class Collection(EdgeCollectionConfig):
        name = "authorships"


class Commentary(EdgeModel):
    commented_at: datetime.datetime

    class Collection(EdgeCollectionConfig):
        name = "commentaries"


class Like(EdgeModel):
    liked_at: datetime.datetime

    class Collection(EdgeCollectionConfig):
        name = "likes"


Post.update_forward_refs()
Comment.update_forward_refs()
User.update_forward_refs()


@pytest.fixture(scope="module", autouse=True)
async def init_collections(session: PydangoSession):
    models: Iterable[Type[BaseArangoModel]] = (Post, Comment, User, Friendship, Authorship, Commentary, Like)
    await asyncio.gather(*[session.init(coll) for coll in models])


@pytest.fixture()
def user():
    user1 = User(name="John", email="john@example.com", age=25)
    user2 = User(name="Alice", email="alice@example.com", age=21)
    post1 = Post(title="First Post", content="This is my first post!")
    comment1 = Comment(
        text="Great post!",
    )

    now = datetime.datetime.now()
    authorship1 = Authorship(created_at=now)
    commentary1 = Commentary(commented_at=now)
    like1 = Like(liked_at=now)
    like2 = Like(liked_at=now)

    user1.likes = [comment1, post1]
    user1.comments = [comment1]
    user1.posts = [post1]
    user1.friends = [user2]

    user1.edges = {
        User.comments: [commentary1],
        User.posts: [authorship1],
        User.likes: [like1, like2],
        User.friends: [Friendship(since=now)],
    }

    post1.comments = [comment1]
    post1.edges = {Post.comments: [commentary1]}
    return user1


def expected_user_depth1(user: VertexModel) -> dict[str, Any]:
    return {
        "_id": ANY_NOT_NONE,
        "_key": ANY_NOT_NONE,
        "_rev": ANY_NOT_NONE,
        "name": "John",
        "age": 25,
        "comments": [{"_id": ANY_NOT_NONE, "_key": ANY_NOT_NONE, "_rev": ANY_NOT_NONE, "text": "Great post!"}],
        "edges": {
            "comments": [
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "commented_at": user.edges.comments[0].commented_at,
                },
            ],
            "friends": [
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "since": user.edges.friends[0].since,
                }
            ],
            "likes": [
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "liked_at": user.edges.likes[0].liked_at,
                },
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "liked_at": user.edges.likes[1].liked_at,
                },
            ],
            "posts": [
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "created_at": user.edges.posts[0].created_at,
                }
            ],
        },
        "email": "john@example.com",
        "friends": [
            {
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "age": 21,
                "comments": None,
                "edges": None,
                "email": "alice@example.com",
                "friends": None,
                "likes": None,
                "name": "Alice",
                "posts": None,
            }
        ],
        "likes": Contains(
            [
                {"_id": ANY_NOT_NONE, "_key": ANY_NOT_NONE, "_rev": ANY_NOT_NONE, "text": "Great post!"},
                {
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "content": "This is my first post!",
                    "title": "First Post",
                },
            ]
        ),
        "posts": [
            {
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "comments": None,
                "content": "This is my first post!",
                "title": "First Post",
            }
        ],
    }


def expected_user_depth2(user: VertexModel):
    new_user: dict[str, Any] = expected_user_depth1(user)
    new_user.update(
        {
            "likes": Contains(
                [
                    {"_id": ANY_NOT_NONE, "_key": ANY_NOT_NONE, "_rev": ANY_NOT_NONE, "text": "Great post!"},
                    {
                        "_id": ANY_NOT_NONE,
                        "_key": ANY_NOT_NONE,
                        "_rev": ANY_NOT_NONE,
                        "content": "This is my first post!",
                        "title": "First Post",
                        "comments": [
                            {"text": "Great post!", "_id": ANY_NOT_NONE, "_rev": ANY_NOT_NONE, "_key": ANY_NOT_NONE}
                        ],
                    },
                ],
            ),
            "posts": [
                {
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "comments": [
                        {"_id": ANY_NOT_NONE, "_key": ANY_NOT_NONE, "_rev": ANY_NOT_NONE, "text": "Great post!"}
                    ],
                    "content": "This is my first post!",
                    "title": "First Post",
                }
            ],
        }
    )
    return new_user


@pytest.mark.run(order=1)
@pytest.mark.asyncio
async def test_save(matcher: Matcher, session: PydangoSession, request: FixtureRequest, user: User):
    await session.save(user)
    request.config.cache.set("user_key", user.key)  # type: ignore[union-attr]
    matcher.assert_declarative_object(user.dict(by_alias=True, include_edges=True), expected_user_depth2(user))


@pytest.mark.run(order=2)
async def test_get(matcher: Matcher, session: PydangoSession, request: FixtureRequest):
    _id = request.config.cache.get("user_key", None)  # type: ignore[union-attr]
    result = await session.get(User, _id, fetch_edges=True, depth=range(1, 1))
    assert result
    expected_user = expected_user_depth1(result)
    matcher.assert_declarative_object(
        result.dict(by_alias=True, include_edges=True),
        expected_user,
        check_order=False,
    )


@pytest.mark.run(order=2)
async def test_get2(matcher: Matcher, session: PydangoSession, request: FixtureRequest):
    _id = request.config.cache.get("user_key", None)  # type: ignore[union-attr]
    result = await session.get(User, _id, fetch_edges=True, depth=range(1, 2))
    assert result
    result_dict = result.dict(by_alias=True, include_edges=True)
    depth = expected_user_depth2(result)
    matcher.assert_declarative_object(result_dict, depth, check_order=False)
