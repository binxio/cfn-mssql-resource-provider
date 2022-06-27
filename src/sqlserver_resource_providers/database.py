import logging
import textwrap
from typing import Optional

from sqlserver_resource_providers import connection_info
from sqlserver_resource_providers.base import SQLServerResource

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


class SQLServerDatabase(SQLServerResource):
    def __init__(self):
        super(SQLServerDatabase, self).__init__()
        self.request_schema = request_schema

    @property
    def name(self) -> str:
        return self.get("Name")

    @property
    def old_name(self) -> str:
        return self.get_old("Name")

    def get_database_id(self) -> Optional[str]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT database_id FROM master.sys.databases 
                    WHERE name = '{SQLServerResource.safe(self.name)}'
                    """
                )
                rows = cursor.fetchone()
        except Exception as e:
            rows = None
            log.error("%s", e)

        return rows[0] if rows else None

    @property
    def url(self):
        return "sqlserver:%s:database:%s" % (
            self.logical_resource_id,
            self.get_database_id(),
        )

    def create(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE [{self.name}]")
            self.physical_resource_id = self.url
            self.set_attribute("Name", self.name)
        except Exception as e:
            self.physical_resource_id = "could-not-create"
            self.fail("Failed to create database, %s" % e)
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
        except Exception as e:
            self.fail("Failed to rename database, %s" % e)
        finally:
            self.close()

    def update(self):
        if self.name != self.old_name:
            if not self.get_database_id():
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
        except Exception as e:
            return self.fail(str(e))
        finally:
            self.close()


provider = SQLServerDatabase()


def handler(request, context):
    return provider.handle(request, context)
