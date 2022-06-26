import boto3
import logging
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
    "required": ["Server", "Name"],
    "properties": {
        "Server": connection_info.request_schema,
        "Name": {
            "type": "string",
            "maxLength": 128,
            "pattern": r"^[^\[\]]*$",
            "description": "the database name to create"
        },
        "DeletionPolicy": {
            "type": "string",
            "default": "Retain",
            "enum": ["Drop", "Retain"]
        }
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


    @property
    def url(self):
        return 'sqlserver://%s:%s/%s' % (self.connection_info['host'], self.connection_info['port'], self.name)

    def create(self):
        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(f'CREATE DATABASE [{self.name}]')
            self.physical_resource_id = self.url
        except Exception as e:
            self.physical_resource_id = 'could-not-create'
            self.fail('Failed to create database, %s' % e)
        finally:
            self.close()

    def update(self):
        if self.name == self.old_name and self.server_url == self.old_server_url:
            self.success('nothing to update here')
            return

        self.fail("changing or moving the database is not supported. too scary.")

    def delete(self):
        if self.physical_resource_id == 'could-not-create':
            self.success('database was never created')
            return

        if self.deletion_policy == 'Retain':
            self.success('deletion policy is retain')
            return

        try:
            self.connect(autocommit=True)
            with self.connection.cursor() as cursor:
                cursor.execute(f'DROP DATABASE IF EXISTS [{self.name}]')
        except Exception as e:
            return self.fail(str(e))
        finally:
            self.close()


provider = SQLServerDatabase()


def handler(request, context):
    return provider.handle(request, context)
