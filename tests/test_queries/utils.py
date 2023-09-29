async def execute_query(query, database):
    return await database.aql.execute(query.compile(), bind_vars=query.bind_vars)
