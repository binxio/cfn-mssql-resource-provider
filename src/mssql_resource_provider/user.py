import logging

import pymssql

from mssql_resource_provider import connection_info
from mssql_resource_provider.base import MSSQLResource

log = logging.getLogger()

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "required": [
        "Server",
        "UserName",
        "LoginName",
    ],
    "properties": {
        "Server": connection_info.request_schema,
        "UserName": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "description": "to create",
        },
        "LoginName": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "description": "to create the user for",
        },
        "DefaultSchema": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "default": "dbo",
            "description": "to connect the user to",
        },
    },
}


class MSSQLUser(MSSQLResource):
    def __init__(self):
        super(MSSQLUser, self).__init__()
        self.request_schema = request_schema

    @property
    def username(self):
        return self.get("UserName")

    @property
    def old_username(self):
        return self.get_old("UserName", self.username)

    @property
    def default_schema(self):
        return self.get("DefaultSchema")

    @property
    def login_name(self):
        return self.get("LoginName")

    @property
    def allow_update(self):
        return self.url == self.physical_resource_id

    @property
    def url(self):
        return "mssql:%s:database:%s:user:%s" % (
            self.logical_resource_id,
            self.get_database_id(self.database),
            self.get_user_id(self.database, self.username),
        )

    @property
    def database(self):
        return self.connection_info["database"]

    def drop_user(self):
        with self.connection.cursor() as cursor:
            cursor.execute(f"DROP USER IF EXISTS [{self.username}]")

    def update_user(self):
        log.info("update user %s", self.username)
        with self.connection.cursor() as cursor:
            if self.username != self.old_username:
                cursor.execute(
                    f"""
                ALTER USER [{self.old_username}] 
                WITH 
                   NAME = [{self.username}], 
                   LOGIN = [{self.login_name}],
                   DEFAULT_SCHEMA = [{self.default_schema}]
                """
                )
            else:
                cursor.execute(
                    f"""
                    ALTER USER [{self.username}] 
                    WITH 
                       LOGIN = [{self.login_name}],
                       DEFAULT_SCHEMA = [{self.default_schema}]
                    """
                )

            self.physical_resource_id = self.url
            self.set_attribute("UserName", self.username)

    def create_user(self):
        log.info("create user %s", self.login_name)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE USER [{self.username}] 
                FOR 
                   LOGIN [{self.login_name}]
                WITH
                   DEFAULT_SCHEMA = [{self.default_schema}]
                """
            )

            self.physical_resource_id = self.url
            self.set_attribute("UserName", self.username)

    def create(self):
        try:
            self.connect()
            self.create_user()
        except pymssql.StandardError as error:
            self.physical_resource_id = "could-not-create"
            self.report_failure(error)
        finally:
            self.close()

    def update(self):
        try:
            self.connect()
            if self.allow_update:
                self.update_user()
            else:
                self.create()
        except pymssql.StandardError as error:
            self.report_failure(error)
        finally:
            self.close()

    def delete(self):
        if self.physical_resource_id == "could-not-create":
            self.success("user was never created")

        try:
            self.connect()
            self.drop_user()
        except pymssql.StandardError as error:
            self.report_failure(error)
        finally:
            self.close()


provider = MSSQLUser()


def handler(request, context):
    return provider.handle(request, context)
