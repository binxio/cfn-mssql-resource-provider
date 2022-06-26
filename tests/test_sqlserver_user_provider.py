import logging
import random
import re
import string
import uuid
from unittest import TestCase

import pymssql

from sqlserver_resource_providers import handler
from sqlserver_resource_providers.connection_info import from_url

logging.basicConfig(level=logging.INFO)



def random_name():
    chars = string.ascii_letters
    return ''.join(random.choice(chars) for i in range(20))


class Event(dict):

    def __init__(self, request_type, user_name, login_name, default_schema='dbo', physical_resource_id=None):
        self.update({
            'RequestType': request_type,
            'ResponseURL': 'https://httpbin.org/put',
            'StackId': 'arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid',
            'RequestId': 'request-%s' % str(uuid.uuid4()),
            'ResourceType': 'Custom::SQLServerUser',
            'LogicalResourceId': 'Whatever',
            'ResourceProperties': {
                'UserName': user_name,
                'LoginName': login_name,
                'Server': {'URL': 'sqlserver://localhost:1444/master', 'Password': 'P@ssW0rd'}
            }})

        if default_schema:
            self['ResourceProperties']['DefaultSchema'] = default_schema

        if physical_resource_id is not None:
            self['PhysicalResourceId'] = physical_resource_id

    def test_owner_connection(self, password=None):
        p = self['ResourceProperties']
        if password is None:
            password = p['Server']['Password']
        args = from_url(p['Server']['URL'], password)
        return pymssql.connect(**args)

    def user_exists(self):
        with self.test_owner_connection() as connection:
            with connection.cursor() as cursor:
                name = self['ResourceProperties']['UserName']
                cursor.execute(f"SELECT name FROM sys.database_principals where name = '{name}'")
                row = cursor.fetchone()
                return row and row[0] == name


class SQLServerUserTestCase(TestCase):

    def __init__(self, tests):
        super(SQLServerUserTestCase, self).__init__(tests)
        self.login_name = random_name()

    def tearDown(self) -> None:
        with Event('XXXX', 'XXXX', 'XXXX').test_owner_connection() as connection:
            connection.autocommit(True)
            with connection.cursor() as c:
                c.execute(
                    f"""
                            DROP LOGIN [{self.login_name}]
                    """
                )


    def setUp(self) -> None:
        with Event('XXXX', 'XXXX', 'XXXX').test_owner_connection() as connection:
            connection.autocommit(True)
            with connection.cursor() as c:
                c.execute(
                    """
                    IF NOT EXISTS(SELECT * FROM master.sys.databases WHERE name = 'alt_db')
                    BEGIN
                        CREATE DATABASE [alt_db]
                    END
                    """)
            with connection.cursor() as c:
                c.execute(
                    f"""
                    CREATE LOGIN [{self.login_name}] WITH PASSWORD = 'P@ssw0rd'
                    """
                )


    def test_invalid_name(self):
        event = Event('Create', 'nicey-nice] ; drop user blalba', self.login_name)
        response = handler(event, {})
        assert response['Status'] == 'FAILED', response['Reason']

    def test_create(self):
        name = random_name()
        event = Event('Create', name, self.login_name)
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        assert 'PhysicalResourceId' in response
        physical_resource_id = response['PhysicalResourceId']
        assert re.match(r'^sqlserver:localhost:1444:master:user:[0-9]+$', physical_resource_id)

        assert event.user_exists()

        event = Event('Create', name, self.login_name)
        response = handler(event, {})
        assert response['Status'] == 'FAILED', '%s' % response['Reason']
        assert 'already exists in' in response['Reason']

        # delete non existing
        event = Event('Delete', name + "-", 'xxxxx', physical_resource_id + '-')
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        event = Event('Delete', name, self.login_name, physical_resource_id)
        event['ResourceProperties']['DeletionPolicy'] = 'Drop'
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        assert not event.user_exists()

    def test_change_database(self):
        name = random_name()
        create_event = Event('Create', name, self.login_name)
        response = handler(create_event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']
        physical_resource_id = response["PhysicalResourceId"]
        assert create_event.user_exists()

        #move user to other db
        event = Event('Update', name, self.login_name, physical_resource_id)
        event['ResourceProperties']['Server'] =  {
            'URL': 'sqlserver://localhost:1444/alt_db',
            'Password': 'P@ssW0rd'}
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']
        physical_resource_id_2 = response["PhysicalResourceId"]
        assert physical_resource_id_2 != physical_resource_id

        assert event.user_exists()

        # delete new user in alt_db
        event['RequestType'] = 'Delete'
        event['PhysicalResourceId'] = physical_resource_id_2
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']

        assert not event.user_exists()

        # delete old user
        event = Event('Delete', name, self.login_name, physical_resource_id)
        response = handler(event, {})
        assert response['Status'] == 'SUCCESS', response['Reason']
        assert not event.user_exists()
