import logging
import textwrap
from typing import Optional

from mssql_resource_provider import connection_info
from mssql_resource_provider.base import MSSQLResource

log = logging.getLogger()

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "required": ["Server", "Name", "Owner"],
    "properties": {
        "Server": connection_info.request_schema,
        "Name": {
            "type": "string",
            "maxLength": 128,
            "pattern": r"^[^\[\]]*$",
            "description": "the database name to create",
        },
        "Owner": {
            "type": "string",
            "maxLength": 128,
            "pattern": r"^[^\[\]]*$",
            "description": "the user owning the schema",
        },
    },
}


class MSSQLSchema(MSSQLResource):
    def __init__(self):
        super(MSSQLSchema, self).__init__()
        self.request_schema = request_schema

    @property
    def name(self) -> str:
        return self.get("Name")

    @property
    def old_name(self) -> str:
        return self.get_old("Name")

    @property
    def owner(self) -> str:
        return self.get("Owner")

    @property
    def old_owner(self) -> str:
        return self.get_old("Owner")

    def get_schema_id(self) -> Optional[str]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT schema_id FROM sys.schemas 
                    WHERE name = '{MSSQLResource.safe(self.name)}'
                    """
                )
                rows = cursor.fetchone()
        except Exception as e:
            rows = None
            log.error("%s", e)

        return rows[0] if rows else None

    @property
    def url(self):
        return "mssql:%s:schema:%s" % (
            self.logical_resource_id,
            self.get_schema_id(),
        )

    def create(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"CREATE SCHEMA [{self.name}] AUTHORIZATION [{self.owner}]"
                )
            self.physical_resource_id = self.url
            self.set_attribute("Name", self.name)
        except Exception as e:
            self.physical_resource_id = "could-not-create"
            self.fail("Failed to create schema, %s" % e)
        finally:
            self.close()

    def change_owner(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"ALTER AUTHORIZATION ON SCHEMA::[{self.name}] TO [{self.owner}]"
                )
            self.set_attribute("Name", self.name)
        except Exception as e:
            self.fail("Failed to change owner, %s" % e)
        finally:
            self.close()

    def update(self):
        if self.name != self.old_name:
            self.fail("schema name cannot be changed")
            return

        if self.owner != self.old_owner:
            self.change_owner()
        else:
            self.success("nothing to update here")

    def delete(self):
        if self.physical_resource_id == "could-not-create":
            self.success("database was never created")
            return

        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(f"DROP SCHEMA [{self.name}]")
        except Exception as e:
            return self.fail(str(e))
        finally:
            self.close()


provider = MSSQLSchema()


def handler(request, context):
    return provider.handle(request, context)
