import logging

import pymssql

from mssql_resource_provider import connection_info
from mssql_resource_provider.base import MSSQLResource

log = logging.getLogger()

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "required": ["Server", "Permission", "UserName", "Database"],
    "properties": {
        "Server": connection_info.request_schema,
        "Permission": {
            "type": "string",
            "maxLength": 128,
            "pattern": r"^[A-Za-z ]+$",
            "description": "to grant on the database",
        },
        "UserName": {
            "type": "string",
            "maxLength": 128,
            "pattern": r"^[^\[\]]*$",
            "description": "to grant the permission to",
        },
        "Database": {
            "type": "string",
            "maxLength": 128,
            "pattern": r"^[^\[\]]*$",
            "description": "to apply the grant to",
        },
    },
}


class MSSQLDatabaseGrant(MSSQLResource):
    def __init__(self):
        super(MSSQLDatabaseGrant, self).__init__()
        self.request_schema = request_schema

    @property
    def permission(self) -> str:
        result = self.get("Permission")
        return result.upper().strip() if result else ""

    @property
    def old_permission(self) -> str:
        result = self.get_old("Permission")
        return result.upper().strip() if result else ""

    @property
    def username(self) -> str:
        return self.get("UserName")

    @property
    def old_username(self) -> str:
        return self.get_old("UserName")

    @property
    def database(self) -> str:
        return self.get("Database")

    @property
    def old_database(self) -> str:
        return self.get_old("Database")

    @property
    def url(self):
        return "mssql:%s:grant:%s:%s:%s" % (
            self.logical_resource_id,
            self.permission,
            self.get_user_id(self.database, self.username),
            self.get_database_id(self.database),
        )

    def grant(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"GRANT {self.permission} ON DATABASE::[{self.database}] TO [{self.username}]"
                )
            self.physical_resource_id = self.url
        except pymssql.Error as error:
            self.physical_resource_id = "could-not-create"
            self.report_failure(error)
        finally:
            self.close()

    def revoke(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"REVOKE {self.permission} ON DATABASE::[{self.database}] FROM [{self.username}]"
                )
        except pymssql.Error as error:
            self.report_failure(error)
        finally:
            self.close()

    def create(self):
        self.grant()

    def update(self):
        self.grant()

    def delete(self):
        if self.physical_resource_id == "could-not-create":
            self.success("database was never created")
            return

        self.revoke()


provider = MSSQLDatabaseGrant()


def handler(request, context):
    return provider.handle(request, context)
