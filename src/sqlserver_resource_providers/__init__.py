from sqlserver_resource_providers import login, user, database


def handler(request, context):
    if request["ResourceType"] == "Custom::SQLServerDatabase":
        return database.handler(request, context)
    elif request["ResourceType"] == "Custom::SQLServerUser":
        return user.handler(request, context)

    return login.handler(request, context)
