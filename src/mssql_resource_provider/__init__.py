from mssql_resource_provider import login, user, database, schema


def handler(request, context):
    if request["ResourceType"] == "Custom::MSSQLDatabase":
        return database.handler(request, context)
    elif request["ResourceType"] == "Custom::MSSQLUser":
        return user.handler(request, context)
    elif request["ResourceType"] == "Custom::MSSQLSchema":
        return schema.handler(request, context)

    return login.handler(request, context)
