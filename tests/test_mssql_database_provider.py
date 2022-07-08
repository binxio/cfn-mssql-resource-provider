import logging
import random
import re
import string
import textwrap
import uuid
from unittest import TestCase

import pymssql
from pymssql import _mssql

from mssql_resource_provider import handler
from mssql_resource_provider.connection_info import from_url

logging.basicConfig(level=logging.INFO)


def random_name():
    chars = string.ascii_letters
    return "".join(random.choice(chars) for i in range(20))


class Event(dict):
    def __init__(self, request_type, db_name, physical_resource_id=None):
        self.update(
            {
                "RequestType": request_type,
                "ResponseURL": "https://httpbin.org/put",
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "RequestId": "request-%s" % str(uuid.uuid4()),
                "ResourceType": "Custom::MSSQLDatabase",
                "LogicalResourceId": "Whatever",
                "ResourceProperties": {
                    "Name": db_name,
                    "Server": {
                        "URL": "mssql://localhost:1444",
                        "Password": "P@ssW0rd",
                    },
                },
            }
        )
        if physical_resource_id is not None:
            self["PhysicalResourceId"] = physical_resource_id

    def test_owner_connection(self, password=None):
        p = self["ResourceProperties"]
        if password is None:
            password = p["Server"]["Password"]
        args = from_url(p["Server"]["URL"], password)
        return pymssql.connect(**args)

    def database_exists(self):
        with self.test_owner_connection() as connection:
            with connection.cursor() as cursor:
                name = self["ResourceProperties"]["Name"]
                cursor.execute(f"SELECT name FROM sys.databases where name = '{name}'")
                row = cursor.fetchone()
                return row and row[0] == name


class MSSQLDatabaseTestCase(TestCase):
    @staticmethod
    def setUpClass() -> None:
        with _mssql.connect(
            server="localhost",
            user="sa",
            port=1444,
            database="master",
            password="P@ssW0rd",
        ) as c:

            sql = textwrap.dedent(
                """
                IF NOT EXISTS(SELECT 1 FROM sys.databases WHERE name = 'rdsadmin')
                BEGIN
                    CREATE DATABASE rdsadmin;
                END
                """
            )
            c.execute_non_query(sql)

        with _mssql.connect(
            server="localhost",
            user="sa",
            port=1444,
            database="rdsadmin",
            password="P@ssW0rd",
        ) as c:
            sql = textwrap.dedent(
                """
                CREATE OR ALTER PROCEDURE rds_modify_db_name(@old_name nvarchar(max), @new_name nvarchar(max))
                AS
                DECLARE @sql nvarchar(max)
                SET @sql = N'alter database [' + @old_name + '] modify name = [' + @new_name + ']'
                PRINT @sql
                exec sp_executesql @sql
                ;
                """
            )
            c.execute_non_query(sql)

    def test_invalid_name(self):
        event = Event("Create", "nicey-nice] ; drop user blalba")
        response = handler(event, {})
        assert response["Status"] == "FAILED", response["Reason"]

    def test_create(self):
        name = random_name()
        event = Event("Create", name)
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        assert "PhysicalResourceId" in response
        physical_resource_id = response["PhysicalResourceId"]
        assert re.match(r"^mssql:[^:]+:database:[0-9]+$", physical_resource_id)

        assert event.database_exists()

        event = Event("Create", name)
        response = handler(event, {})
        assert response["Status"] == "FAILED", "%s" % response["Reason"]
        assert "already exists." in response["Reason"]

        # delete non existing
        event = Event("Delete", name + "-", physical_resource_id + "-")
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        event = Event("Delete", name, physical_resource_id)
        event["ResourceProperties"]["DeletionPolicy"] = "Drop"
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        assert not event.database_exists()

    def test_rename(self):
        name = random_name()
        new_name = f"new-{name}"
        event = Event("Create", name)
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]
        physical_resource_id = response["PhysicalResourceId"]
        assert re.match(r"^mssql:[^:]+:database:[0-9]+$", physical_resource_id)

        event = Event("Update", new_name, physical_resource_id)
        event["OldResourceProperties"] = {"Name": name}
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]
        new_physical_resource_id = response["PhysicalResourceId"]

        assert physical_resource_id == new_physical_resource_id
