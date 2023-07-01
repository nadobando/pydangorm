import datetime
from typing import Annotated, List, Optional, Type, Union
from unittest.mock import ANY

import pytest
from aioarango.database import StandardDatabase

from pydango.connection.session import PydangoSession
from pydango.orm.models import (
    BaseArangoModel,
    EdgeCollectionConfig,
    EdgeModel,
    Relation,
    VertexCollectionConfig,
    VertexModel,
)
from tests.utils import assert_equals_dicts


class Post(VertexModel):
    title: str
    content: str
    # todo: make this work
    # author: Annotated["User", BackRelation["Authorship"]]
    comments: Annotated[Optional[List["Comment"]], Relation["PostComment"]] = None

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
    comments: Annotated[Optional[List["Comment"]], Relation["Commentary"]] = None
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


class PostComment(EdgeModel):
    connection: str

    class Collection(EdgeCollectionConfig):
        name = "post_comments"


class Like(EdgeModel):
    liked_at: datetime.datetime

    class Collection(EdgeCollectionConfig):
        name = "likes"


Post.update_forward_refs()
Comment.update_forward_refs()
User.update_forward_refs()

user1 = User(name="John", email="john@example.com", age=25)
user2 = User(name="Jane", email="jane@example.com", age=30)
user3 = User(name="Alice", email="alice@example.com", age=28)
user4 = User(name="Bob", email="bob@example.com", age=32)

friendship1 = Friendship(since=datetime.date(2020, 1, 1))
friendship2 = Friendship(since=datetime.date(2021, 3, 15))
friendship3 = Friendship(since=datetime.date(2022, 5, 10))
friendship4 = Friendship(since=datetime.date(2023, 2, 20))

authorship1 = Authorship(created_at=datetime.datetime.now())
authorship2 = Authorship(created_at=datetime.datetime.now())
authorship3 = Authorship(created_at=datetime.datetime.now())

commentary1 = Commentary(commented_at=datetime.datetime.now())
commentary2 = Commentary(commented_at=datetime.datetime.now())

post1 = Post(title="First Post", content="This is my first post!")
post2 = Post(title="Second Post", content="This is my second post!")

comment1 = Comment(text="Great post!")
comment2 = Comment(text="I enjoyed reading this.")

like1 = Like(liked_at=datetime.datetime.now())
like2 = Like(liked_at=datetime.datetime.now())
like3 = Like(liked_at=datetime.datetime.now())

user1.friends = [user2, user3, user4]
user1.posts = [post1]
user1.comments = [comment1, comment2]
user1.likes = [comment2]

# user2.friends = [user1, user3]
# user2.posts = [post1]
# user2.comments = [comment1]
# user2.likes = [post1]
#
# user3.friends = [user1, user2]
# user3.posts = [post2]
# user3.comments = [comment2]
# user3.likes = [comment1]
#
# user4.friends = [user1]
# user4.posts = [post2]
# user4.comments = [comment2]
# user4.likes = [comment1, comment2]
#
user1.edges = {
    User.friends: [friendship1, friendship2, friendship3],
    User.comments: [commentary1, commentary2],
    User.posts: [authorship1],
    User.likes: [like1],
}

# user2.edges = {
#     User.friends: [friendship1, friendship2],
#     User.posts: [authorship1],
#     User.comments: [commentary1],
#     User.likes: [like1],
# }
#
# user3.edges = {
#     User.friends: [friendship1, friendship3],
#     User.posts: [authorship2],
#     User.comments: [commentary2],
#     User.likes: [comment1],
# }
#
# user4.edges = {
#     User.friends: [friendship4],
#     User.posts: [authorship2],
#     User.comments: [comment2],
#     User.likes: [comment1, comment2],
# }

# post1.author = user1
post1.comments = [comment1]


# post2.author = user1
# post2.comments = [comment2]

# comment1.author = user1
# comment1.post = post1

# comment2.author = user3
# comment2.post = post2

# comment1.likes = [like1, like2]
# comment2.likes = [like3]


@pytest.mark.asyncio
async def test_save(database: StandardDatabase):
    session = PydangoSession(database)
    models: list[Type[BaseArangoModel]] = []
    models += VertexModel.__subclasses__()
    models += EdgeModel.__subclasses__()
    for i in models:
        await session.init(i)

    await session.save(user1)

    expected = {
        "_id": ANY,
        "_key": ANY,
        "_rev": ANY,
        "age": 25,
        "comments": [
            {"_id": ANY, "_key": ANY, "_rev": ANY, "text": "Great post!"},
            {"_id": ANY, "_key": ANY, "_rev": ANY, "text": "I enjoyed reading this."},
        ],
        "edges": {
            "comments": [
                {
                    "_from": ANY,
                    "_id": ANY,
                    "_key": ANY,
                    "_rev": ANY,
                    "_to": ANY,
                    "commented_at": datetime.datetime(2023, 7, 1, 18, 53, 20, 121092),
                },
                {
                    "_from": ANY,
                    "_id": ANY,
                    "_key": ANY,
                    "_rev": ANY,
                    "_to": ANY,
                    "commented_at": datetime.datetime(2023, 7, 1, 18, 53, 20, 121098),
                },
            ],
            "friends": [
                {
                    "_from": ANY,
                    "_id": ANY,
                    "_key": ANY,
                    "_rev": ANY,
                    "_to": ANY,
                    "since": datetime.date(2020, 1, 1),
                },
                {
                    "_from": ANY,
                    "_id": ANY,
                    "_key": ANY,
                    "_rev": ANY,
                    "_to": ANY,
                    "since": datetime.date(2021, 3, 15),
                },
                {
                    "_from": ANY,
                    "_id": ANY,
                    "_key": ANY,
                    "_rev": ANY,
                    "_to": ANY,
                    "since": datetime.date(2022, 5, 10),
                },
            ],
            "likes": [
                {
                    "_from": ANY,
                    "_id": ANY,
                    "_key": ANY,
                    "_rev": ANY,
                    "_to": ANY,
                    "liked_at": datetime.datetime(2023, 7, 1, 18, 53, 20, 121134),
                }
            ],
            "posts": [
                {
                    "_from": ANY,
                    "_id": ANY,
                    "_key": ANY,
                    "_rev": ANY,
                    "_to": ANY,
                    "created_at": datetime.datetime(2023, 7, 1, 18, 53, 20, 121070),
                }
            ],
        },
        "email": "john@example.com",
        "friends": [
            {
                "_id": ANY,
                "_key": ANY,
                "_rev": ANY,
                "age": 30,
                "comments": None,
                "edges": None,
                "email": "jane@example.com",
                "friends": None,
                "likes": None,
                "name": "Jane",
                "posts": None,
            },
            {
                "_id": ANY,
                "_key": ANY,
                "_rev": ANY,
                "age": 28,
                "comments": None,
                "edges": None,
                "email": "alice@example.com",
                "friends": None,
                "likes": None,
                "name": "Alice",
                "posts": None,
            },
            {
                "_id": ANY,
                "_key": ANY,
                "_rev": ANY,
                "age": 32,
                "comments": None,
                "edges": None,
                "email": "bob@example.com",
                "friends": None,
                "likes": None,
                "name": "Bob",
                "posts": None,
            },
        ],
        "likes": [{"_id": ANY, "_key": ANY, "_rev": ANY, "text": "I enjoyed reading this."}],
        "name": "John",
        "posts": [
            {
                "_id": ANY,
                "_key": ANY,
                "_rev": ANY,
                "comments": [{"_id": "comments/62920", "_key": "62920", "_rev": "_gPGmmm2--D", "text": "Great post!"}],
                "content": "This is my first post!",
                "title": "First Post",
            }
        ],
    }
    assert_equals_dicts(expected, user2.dict(by_alias=True, include_edges=True))
