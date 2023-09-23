import datetime

from pydango.orm.models import Aliased, VertexCollectionConfig, VertexModel
from pydango.orm.query import ORMQuery
from pydango.query.expressions import (
    NEW,
    OLD,
    AssignmentExpression,
    IteratorExpression,
    VariableExpression,
)
from pydango.query.functions import Sum


class User(VertexModel):
    name: str
    age: int

    class Collection(VertexCollectionConfig):
        name = "users"


class Post(VertexModel):
    created_date: datetime.datetime
    user: str
    likes: int

    class Collection(VertexCollectionConfig):
        name = "posts"


def test_simple_query():
    orm_query = ORMQuery()
    aql = orm_query.for_(User).filter(User.age > 10).sort(+User.age).return_(User)
    i = aql.orm_bound_vars[User]
    expected_repr = (
        f"FOR {repr(i)} IN <CollectionExpression: users> FILTER {repr(i)}.age > ? SORT {repr(i)}.age ASC RETURN"
        f" {repr(i)}"
    )
    expected_compilation = "FOR var1 IN `users` FILTER var1.age > @param1 SORT var1.age ASC RETURN var1"

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compilation


def test_named_aliased():
    aliased_user = Aliased(User, "u")
    aql = ORMQuery().for_(aliased_user).filter(aliased_user.age > 10).sort(-aliased_user.age).return_(aliased_user)
    i = aql.orm_bound_vars[aliased_user]
    expected_compiled = "FOR u IN `users` FILTER u.age > @param1 SORT u.age DESC RETURN u"
    expected_repr = (
        f"FOR {repr(i)} IN <CollectionExpression: users> FILTER {repr(i)}.age > ? SORT {repr(i)}.age DESC RETURN"
        f" {repr(i)}"
    )

    assert repr(aql) == expected_repr
    assert expected_compiled == aql.compile()


def test_aliased():
    aliased_user = Aliased(User)
    orm_query = ORMQuery()
    aql = orm_query.for_(aliased_user).filter(aliased_user.age > 10).sort(-aliased_user.age).return_(aliased_user)
    i = aql.orm_bound_vars[aliased_user]
    expected_compiled = "FOR var1 IN `users` FILTER var1.age > @param1 SORT var1.age DESC RETURN var1"
    expected_repr = (
        f"FOR {repr(i)} IN <CollectionExpression: users> FILTER {repr(i)}.age > ? SORT {repr(i)}.age DESC RETURN"
        f" {repr(i)}"
    )

    assert repr(aql) == expected_repr
    assert expected_compiled == aql.compile()


def test_projected_object():
    aliased_user = Aliased(User)
    aliased2 = Aliased(User, "u1")
    aql = (
        ORMQuery()
        .for_(aliased_user)
        .for_(aliased2)
        .filter(aliased_user.age > aliased2.age)
        .return_({"user1": aliased_user.age, "user2": aliased2.age})
    )
    i1 = aql.orm_bound_vars[aliased_user]
    i2 = aql.orm_bound_vars[aliased2]
    expected_compiled = (
        "FOR var1 IN `users` FOR u1 IN `users` FILTER var1.age > u1.age RETURN {user1: var1.age, user2: u1.age}"
    )
    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> FOR {repr(i2)} IN <CollectionExpression: users> FILTER"
        f" {repr(i1)}.age > {repr(i2)}.age "
        f"RETURN {{user1: {repr(aliased_user)}.age, user2: {repr(aliased2)}.age}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_binary_expression():
    delta = datetime.datetime.now() - datetime.timedelta(seconds=86400)
    aql = (
        ORMQuery()
        .for_(User)
        .for_(Post)
        .filter((Post.user == User.id) & (Post.created_date > delta))
        .sort(+Post.likes, -User.age)
        .return_(User)
    )
    i1 = aql.orm_bound_vars[User]
    i2 = aql.orm_bound_vars[Post]

    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"FOR {repr(i2)} IN <CollectionExpression: posts> "
        f"FILTER {repr(i2)}.user == {repr(i1)}.id &&"
        f" {repr(i2)}.created_date > ? "
        f"SORT {repr(i2)}.likes ASC, {repr(i1)}.age DESC "
        f"RETURN {repr(i1)}"
    )

    expected_compiled = (
        "FOR var1 IN `users` "
        "FOR var2 IN `posts` "
        "FILTER (var2.user == var1.id && var2.created_date > @param1) "
        "SORT var2.likes ASC, var1.age DESC "
        "RETURN var1"
    )
    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_sub_query():
    aql = ORMQuery()
    subquery = ORMQuery().for_(User).filter(User.age > 10).return_(User)

    # # #
    iterator = IteratorExpression()
    aql.for_(iterator, in_=subquery).filter(iterator.likes > 1000).return_(iterator)
    i1 = aql.orm_bound_vars[User]
    expected_repr = (
        # fmt: off
        f"FOR {repr(iterator)} IN ("
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"FILTER {repr(i1)}.age > ? "
        f"RETURN {repr(i1)}"
        f") "
        f"FILTER {repr(iterator)}.likes > ? "
        f"RETURN {repr(iterator)}"
        # fmt: on
    )
    expected_compiled = (
        "FOR var1 IN (FOR var2 IN `users` "
        "FILTER var2.age > @param1 RETURN var2) FILTER var1.likes > @param2 RETURN var1"
    )

    assert repr(aql) == expected_repr

    assert aql.compile() == expected_compiled


def test_insert():
    aql = ORMQuery().insert(User(name="john", age=35)).return_(NEW())
    expected_repr = "INSERT {name: ?, age: ?} INTO <CollectionExpression: users> RETURN NEW"
    expected_compiled = "INSERT {name: @param1, age: @param2} INTO `users` RETURN NEW"
    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_remove():
    aql = ORMQuery().remove(User(key="user/123", name="john", age=35)).return_(OLD())
    expected_repr = "REMOVE {_key: ?} IN <CollectionExpression: users> RETURN OLD"
    expected_compiled = "REMOVE {_key: @param1} IN `users` RETURN OLD"
    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_replace():
    aql = ORMQuery().replace(User(name="john", age=35), User(name="john", age=36)).return_(NEW())
    expected_repr = "REPLACE {name: ?, age: ?} IN <CollectionExpression: users> RETURN NEW"
    expected_compiled = "REPLACE {name: @param1, age: @param2} IN `users` RETURN NEW"
    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_update():
    aql = ORMQuery().update(User(name="john", age=35), User(name="john", age=36)).return_(NEW())
    expected_repr = "UPDATE {name: ?, age: ?} IN <CollectionExpression: users> RETURN NEW"
    expected_compiled = "UPDATE {name: @param1, age: @param2} IN `users` RETURN NEW"
    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_upsert():
    user = User(name="john", age=36)
    aql = ORMQuery().upsert(User(name="john", age=35), insert=user, update=user).return_(NEW())
    expected_repr = (
        "UPSERT {name: ?, age: ?} INSERT {name: ?, age: ?} UPDATE {name: ?, age: ?} IN <CollectionExpression: users>"
        " RETURN NEW"
    )
    expected_compiled = (
        "UPSERT {name: @param1, age: @param3} INSERT {name: @param1, age: @param2} UPDATE {name: @param1, age: @param2}"
        " IN `users` RETURN NEW"
    )
    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect():
    age_collect = VariableExpression()
    assignment_expression = AssignmentExpression(age_collect, User.age)
    aql = (
        ORMQuery()
        .for_(User)
        .collect(
            collect=assignment_expression,
        )
        .return_(age_collect)
    )
    i1 = aql.orm_bound_vars[User]
    expected_compiled = "FOR var1 IN `users` COLLECT var2 = var1.age RETURN var2"
    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"COLLECT {repr(assignment_expression)} "
        f"RETURN {repr(age_collect)}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_into():
    groups = VariableExpression()
    age_collect = VariableExpression()
    assignment_expression = AssignmentExpression(age_collect, User.age)
    aql = (
        ORMQuery()
        .for_(User)
        .collect(collect=assignment_expression, into=groups)
        .return_({"groups": groups, "ages": age_collect})
    )
    i1 = aql.orm_bound_vars[User]
    expected_compiled = "FOR var1 IN `users` COLLECT var2 = var1.age INTO var3 RETURN {groups: var3, ages: var2}"
    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"COLLECT {repr(assignment_expression)} "
        f"INTO {repr(groups)} "
        f"RETURN {{groups: {repr(groups)}, ages: {repr(age_collect)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_into_projection():
    groups = VariableExpression()
    into_expression = AssignmentExpression(groups, User.name)
    ages_collect = VariableExpression()

    assignment_expression = AssignmentExpression(ages_collect, User.age)
    aql = (
        ORMQuery()
        .for_(User)
        .collect(collect=assignment_expression, into=into_expression)
        .return_({"groups": groups, "ages": ages_collect})
    )
    i1 = aql.orm_bound_vars[User]

    expected_compiled = (
        "FOR var1 IN `users` COLLECT var2 = var1.age INTO var3 = var1.name RETURN {groups: var3, ages: var2}"
    )
    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"COLLECT {assignment_expression} "
        f"INTO {repr(into_expression)} "
        f"RETURN {{groups: {repr(groups)}, ages: {repr(ages_collect)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_with_count():
    length = VariableExpression()
    category_collect = VariableExpression()
    assignment_expression = AssignmentExpression(category_collect, User.age)
    aql = (
        ORMQuery()
        .for_(User)
        .collect(collect=assignment_expression, with_count_into=length)
        .return_({"length": length, "categories": category_collect})
    )
    i1 = aql.orm_bound_vars[User]

    expected_compiled = (
        "FOR var1 IN `users` COLLECT var2 = var1.age WITH COUNT INTO var3 RETURN {length: var3, categories: var2}"
    )
    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"COLLECT {repr(assignment_expression)} "
        f"WITH COUNT INTO {repr(length)} "
        f"RETURN {{length: {repr(length)}, categories: {repr(category_collect)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_aggregate():
    name_collect = VariableExpression()
    ages_agg = VariableExpression()
    collect_expression = AssignmentExpression(name_collect, User.name)
    aggregate_expression = AssignmentExpression(ages_agg, Sum(User.age))
    aql = (
        ORMQuery()
        .for_(User)
        .collect(
            collect=collect_expression,
            aggregate=aggregate_expression,
        )
        .return_({"groups": name_collect, "ages": ages_agg})
    )
    i1 = aql.orm_bound_vars[User]

    expected_compiled = (
        "FOR var1 IN `users` COLLECT var2 = var1.name AGGREGATE var3 = SUM(var1.age) RETURN {groups: var2, ages: var3}"
    )
    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"COLLECT {repr(collect_expression)} "
        f"AGGREGATE {repr(aggregate_expression)} "
        f"RETURN {{groups: {repr(name_collect)}, ages: {repr(ages_agg)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_aggregate_into():
    groups = VariableExpression()

    name_collect = VariableExpression()
    ages_agg = VariableExpression()
    collect_expression = AssignmentExpression(name_collect, User.name)
    aggregate_expression = AssignmentExpression(ages_agg, Sum(User.age))
    aql = (
        ORMQuery()
        .for_(User)
        .collect(collect=collect_expression, aggregate=aggregate_expression, into=groups)
        .return_({"names": name_collect, "ages": ages_agg, "groups": groups})
    )
    i1 = aql.orm_bound_vars[User]

    expected_compiled = (
        "FOR var1 IN `users` COLLECT var2 = var1.name AGGREGATE var3 = SUM(var1.age) "
        "INTO var4 "
        "RETURN {names: var2, ages: var3, groups: var4}"
    )
    expected_repr = (
        f"FOR {repr(i1)} IN <CollectionExpression: users> "
        f"COLLECT {repr(collect_expression)} "
        f"AGGREGATE {repr(aggregate_expression)} "
        f"INTO {repr(groups)} "
        f"RETURN {{names: {repr(name_collect)}, ages: {repr(ages_agg)}, groups: {repr(groups)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled
