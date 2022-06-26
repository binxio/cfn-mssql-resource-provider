import boto3
import logging
from typing import Optional
import pymssql
from botocore.exceptions import ClientError
from cfn_resource_provider import ResourceProvider

from sqlserver_resource_providers import connection_info
from sqlserver_resource_providers.base import SQLServerResource
from sqlserver_resource_providers.connection_info import _get_password_from_dict

log = logging.getLogger()

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "required": ["Server", "UserName", "LoginName",],
    "properties": {
        "Server": connection_info.request_schema,
        "UserName": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "description": "to create"
        },
        "LoginName": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "description": "to create the user for"
        },
        "DefaultSchema": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "default": "dbo",
            "description": "to connect the user to"
        },
    },
}

class SQLServerUser(SQLServerResource):

    def __init__(self):
        super(SQLServerUser, self).__init__()
        self.request_schema = request_schema

    @property
    def user_name(self):
        return self.get('UserName')

    @property
    def old_user_name(self):
        return self.get_old('UserName', self.user_name)

    @property
    def default_schema(self):
        return self.get('DefaultSchema')

    @property
    def login_name(self):
        return self.get('LoginName')

    @property
    def allow_update(self):
        return self.url == self.physical_resource_id

    @property
    def url(self):
        return 'sqlserver:%s:%s:%s:user:%s' % (
            self.connection_info['host'],
            self.connection_info['port'],
            self.database,
            self.get_user_id())

    @property
    def database(self):
        return self.connection_info['database']

    def get_user_id(self) -> Optional[str]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT principal_id FROM [{self.database}].sys.database_principals 
                    WHERE name = '{SQLServerResource.safe(self.user_name)}'
                    """)
                rows = cursor.fetchone()
        except Exception as e:
            rows = None
            log.error("%s", e)

        return rows[0] if rows else None
        
    def drop_user(self):
        with self.connection.cursor() as cursor:
            cursor.execute(f'DROP USER IF EXISTS [{self.user_name}]')

    def update_user(self):
        log.info('update user %s', self.user_name)
        with self.connection.cursor() as cursor:
            if self.user_name != self.old_user_name:
                cursor.execute(f"""
                ALTER USER [{self.old_user_name}] 
                WITH 
                   NAME = [{self.user_name}], 
                   LOGIN = [{self.login_name}],
                   DEFAULT_SCHEMA = [{self.default_schema}]
                """)
            else:
                cursor.execute(f"""
                ALTER USER [{self.user_name}] 
                WITH 
                   LOGIN = [{self.login_name}],
                   DEFAULT_SCHEMA = [{self.default_schema}]
                """)


    def create_user(self):
        log.info('create user %s', self.login_name)
        with self.connection.cursor() as cursor:
            cursor.execute(f"""
            CREATE USER [{self.user_name}] 
            FOR 
               LOGIN [{self.login_name}]
            WITH
               DEFAULT_SCHEMA = [{self.default_schema}]
            """)

            self.physical_resource_id = self.url

    def create(self):
        try:
            self.connect()
            self.create_user()
        except Exception as e:
            self.physical_resource_id = 'could-not-create'
            self.fail('Failed to create user, %s' % e)
        finally:
            self.close()

    def update(self):
        try:
            self.connect()
            if self.allow_update:
                self.update_user()
            else:
                self.create()
        except Exception as e:
            self.fail('Failed to update the user, %s' % e)
        finally:
            self.close()

    def delete(self):
        if self.physical_resource_id == 'could-not-create':
            self.success('user was never created')

        try:
            self.connect()
            self.drop_user()
        except Exception as e:
            return self.fail(str(e))
        finally:
            self.close()


provider = SQLServerUser()


def handler(request, context):
    return provider.handle(request, context)
