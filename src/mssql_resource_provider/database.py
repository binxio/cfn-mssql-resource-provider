import logging

import pymssql

from mssql_resource_provider import connection_info
from mssql_resource_provider.base import MSSQLResource

log = logging.getLogger()

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "required": ["Server", "Name"],
    "properties": {
        "Server": connection_info.request_schema,
        "Name": {
            "type": "string",
            "maxLength": 128,
            "pattern": r"^[^\[\]]*$",
            "description": "the database name to create",
        },
    },
}


class MSSQLDatabase(MSSQLResource):
    def __init__(self):
        super(MSSQLDatabase, self).__init__()
        self.request_schema = request_schema

    @property
    def name(self) -> str:
        return self.get("Name")

    @property
    def old_name(self) -> str:
        return self.get_old("Name")

    @property
    def url(self):
        return "mssql:%s:database:%s" % (
            self.logical_resource_id,
            self.get_database_id(self.name),
        )

    def create(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE [{self.name}]")
            self.physical_resource_id = self.url
            self.set_attribute("Name", self.name)
        except pymssql.StandardError as error:
            self.physical_resource_id = "could-not-create"
            self.report_failure(error)
        finally:
            self.close()

    def rename_database(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.callproc(
                    "rdsadmin.dbo.rds_modify_db_name", (self.old_name, self.name)
                )
            self.physical_resource_id = self.url
            self.set_attribute("Name", self.name)
        except pymssql.StandardError as error:
            self.report_failure(error)
        finally:
            self.close()

    def database_exists(self, name: str) -> bool:
        try:
            self.connect(autocommit=True)
            return self.get_database_id(self.name)
        finally:
            self.close()

    def update(self):
        if self.name != self.old_name:
            if not self.database_exists(self.name):
                self.rename_database()
            else:
                self.fail(f"database {self.name} already exists")
        else:
            self.success("nothing to update here")

    def delete(self):
        if self.physical_resource_id == "could-not-create":
            self.success("database was never created")
            return

        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS [{self.name}]")
        except pymssql.StandardError as error:
            self.report_failure(error)
        finally:
            self.close()


provider = MSSQLDatabase()


def handler(request, context):
    return provider.handle(request, context)
