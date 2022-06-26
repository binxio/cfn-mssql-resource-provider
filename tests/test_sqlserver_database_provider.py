import sys
import random, string
import uuid
import pymssql
import boto3
import logging
from hashlib import md5
from sqlserver_resource_providers import handler
from sqlserver_resource_providers.connection_info import from_url
from unittest import TestCase

logging.basicConfig(level=logging.INFO)



def random_name():
    chars = string.ascii_letters
    return ''.join(random.choice(chars) for i in range(20))


class Event(dict):
    def __init__(self, request_type, db_name, physical_resource_id=None):
        self.update({
            'RequestType': request_type,
            'ResponseURL': 'https://httpbin.org/put',
            'StackId': 'arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid',
            'RequestId': 'request-%s' % str(uuid.uuid4()),
            'ResourceType': 'Custom::SQLServerDatabase',
            'LogicalResourceId': 'Whatever',
            'ResourceProperties': {
                'Name': db_name,
                'Server': {'URL': 'sqlserver://localhost:1444', 'Password': 'P@ssW0rd'}
            }})
        if physical_resource_id is not None:
            self['PhysicalResourceId'] = physical_resource_id

    def test_owner_connection(self, password=None):
        p = self['ResourceProperties']
        if password is None:
            password = p['Server']['Password']
        args = from_url(p['Server']['URL'], password)
        return pymssql.connect(**args)

    def database_exists(self):
        with self.test_owner_connection() as connection:
            with connection.cursor() as cursor:
                name = self['ResourceProperties']['Name']
                cursor.execute(f"SELECT name FROM sys.databases where name = '{name}'")
                row = cursor.fetchone()
                return row and row[0] == name


class SQLServerDatabaseTestCase(TestCase):

    def test_invalid_name(self):
        event = Event('Create', 'nicey-nice] ; drop user blalba')
        response = handler(event, {})
        assert response['Status'] == 'FAILED', response['Reason']

    def test_create(self):
        # create a database
        name = random_name()
        event = Event('Create', name)
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        assert 'PhysicalResourceId' in response
        physical_resource_id = response['PhysicalResourceId']
        expect_id = f'sqlserver://localhost:1444/{name}'
        assert physical_resource_id == expect_id, 'expected %s, got %s' % (expect_id, physical_resource_id)

        assert event.database_exists()

        event = Event('Create', name)
        response = handler(event, {})
        assert response['Status'] == 'FAILED', '%s' % response['Reason']
        assert 'already exists.' in response['Reason']

        # delete non existing
        event = Event('Delete', name + "-", physical_resource_id + '-')
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        # delete with retain policy
        event = Event('Delete', name, physical_resource_id)
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        assert event.database_exists()

        event = Event('Delete', name, physical_resource_id)
        event['ResourceProperties']['DeletionPolicy'] = 'Drop'
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        assert not event.database_exists()

