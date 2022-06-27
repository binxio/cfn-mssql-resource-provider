import boto3
import logging
import pymssql
from botocore.exceptions import ClientError
from cfn_resource_provider import ResourceProvider
from typing import Optional
from sqlserver_resource_providers import connection_info
from sqlserver_resource_providers.base import SQLServerResource
from sqlserver_resource_providers.connection_info import _get_password_from_dict

log = logging.getLogger()

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "oneOf": [
        {"required": ["Server", "LoginName", "Password"]},
        {"required": ["Server", "LoginName", "PasswordParameterName"]},
    ],
    "properties": {
        "Server": connection_info.request_schema,
        "LoginName": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "description": "the login name in to create",
        },
        "DefaultDatabase": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "default": "master",
            "description": "the default database name to login to",
        },
        "Password": {"type": "string", "description": "the password for the login"},
        "PasswordParameterName": {
            "type": "string",
            "minLength": 1,
            "description": "the name of the password in the Parameter Store.",
        },
    },
}


class SQLServerLogin(SQLServerResource):
    def __init__(self):
        super(SQLServerLogin, self).__init__()
        self.request_schema = request_schema

    @property
    def password(self) -> str:
        return _get_password_from_dict(self.properties, self.ssm)

    @property
    def login_name(self):
        return self.get("LoginName")

    @property
    def old_login_name(self):
        return self.get_old("LoginName", self.login_name)

    @property
    def default_database(self):
        return self.get("DefaultDatabase")

    @property
    def url(self):
        return "sqlserver:{}:login:{}".format(
            self.logical_resource_id,
            self.get_principal_id(),
        )

    def get_principal_id(self) -> Optional[str]:
        rows = []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT principal_id FROM master.sys.server_principals WHERE name = '{SQLServerResource.safe(self.login_name)}'"
                )
                rows = cursor.fetchone()
        except Exception as e:
            logging.error("%s", e)

        return rows[0] if rows else None

    def drop_login(self):
        log.info("drop login %s", self.login_name)
        with self.connection.cursor() as cursor:
            cursor.execute(f"DROP LOGIN [{self.login_name}]")

    def update_login(self):
        log.info("update login %s", self.login_name)
        with self.connection.cursor() as cursor:
            if self.old_login_name != self.login_name:
                cursor.execute(
                    f"""
                   ALTER LOGIN [{self.old_login_name}]
                   WITH PASSWORD = '{SQLServerResource.safe(self.password)}',
                        NAME = [{self.login_name}],
                        DEFAULT_DATABASE = [{self.default_database}]
                   """
                )
            else:
                cursor.execute(
                    f"""
                   ALTER LOGIN [{self.login_name}]
                   WITH PASSWORD = '{SQLServerResource.safe(self.password)}',
                        DEFAULT_DATABASE = [{self.default_database}]
                   """
                )

            self.physical_resource_id = self.url
            self.set_attribute("LoginName", self.login_name)

    def create_login(self):
        log.info("create login %s", self.login_name)
        with self.connection.cursor() as cursor:
            sql = f"""
               CREATE LOGIN [{self.login_name}]
               WITH PASSWORD = '{SQLServerResource.safe(self.password)}',
                    DEFAULT_DATABASE = [{self.default_database}]
               """
            cursor.execute(sql)

            self.physical_resource_id = self.url
            self.set_attribute("LoginName", self.login_name)

    def create(self):
        try:
            self.connect()
            self.create_login()
        except Exception as e:
            self.physical_resource_id = "could-not-create"
            self.fail("Failed to create user, %s" % e)
        finally:
            self.close()

    def update(self):
        try:
            self.connect()
            self.update_login()
        except Exception as e:
            self.fail("Failed to update the login, %s" % e)
        finally:
            self.close()

    def delete(self):
        if self.physical_resource_id == "could-not-create":
            self.success("login was never created")

        try:
            self.connect()
            if self.get_principal_id():
                self.drop_login()
        except Exception as e:
            return self.fail(str(e))
        finally:
            self.close()


provider = SQLServerLogin()


def handler(request, context):
    return provider.handle(request, context)
