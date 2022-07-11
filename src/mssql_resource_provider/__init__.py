from mssql_resource_provider import login, user, database, grant


def handler(request, context):
    if request["ResourceType"] == "Custom::MSSQLDatabase":
        return database.handler(request, context)
    elif request["ResourceType"] == "Custom::MSSQLUser":
        return user.handler(request, context)
    elif request["ResourceType"] == "Custom::MSSQLDatabaseGrant":
        return grant.handler(request, context)

    return login.handler(request, context)
