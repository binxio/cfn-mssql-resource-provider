import logging
import random
import string

import pymssql

from cfn_resource_provider_test import CloudformationCustomProviderTestCase, Request
from mssql_resource_provider.schema import MSSQLSchema

logging.basicConfig(level=logging.INFO)


def random_name():
    chars = string.ascii_letters
    return "".join(random.choice(chars) for i in range(20))


class MSSQLSchemaTestCase(CloudformationCustomProviderTestCase):
    def connect(self):
        return pymssql.connect(
            server="localhost",
            user="sa",
            port=1444,
            database="master",
            password="P@ssW0rd",
        )

    def new_login_and_user(self, name) -> str:
        with self.connect() as connection:
            connection.cursor().execute(
                f"CREATE LOGIN [{name}] WITH PASSWORD = '{name}!'"
            )
            connection.cursor().execute(f"CREATE USER [{name}] FOR LOGIN [{name}]")
            connection.commit()

    def drop_login_and_user(self, name) -> str:
        with self.connect() as connection:
            try:
                connection.cursor().execute(f"DROP USER IF EXISTS [{self.owner}]")
            except Exception as e:
                logging.info("drop user failed", e)
            try:
                connection.cursor().execute(f"DROP LOGIN [{self.owner}]")
            except Exception as e:
                logging.info("drop login failed", e)

            connection.commit()

    def assert_schema_and_owner(self, name, owner):
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f""" 
                select s.name, p.name from sys.schemas s, sys.database_principals p
                where s.principal_id = p.principal_id 
                and s.name = '{name}' and p.name = '{owner}'
                """
            )
            cursor.fetchone()

    def setUp(self):
        super().setUp()
        self.provider = MSSQLSchema()
        self.owner = random_name()
        self.name = random_name()
        self.new_login_and_user(self.owner)

    def tearDown(self) -> None:
        super().tearDown()
        self.drop_login_and_user(self.owner)

    def test_invalid_name(self):
        request = Request(
            "Custom::MSSQLSchema",
            "Create",
            None,
            {
                "Name": "nicey-nice] ; drop user sa",
                "Owner": self.owner,
                "Server": {
                    "URL": "mssql://localhost:1444/master",
                    "Password": "P@ssW0rd",
                },
            },
        )
        response = self.handle(request)
        self.assertEqual("FAILED", response["Status"], response["Reason"])
        self.assertRegex(response["Reason"], r"^invalid resource properties.*")

    def test_create(self):
        request = Request(
            "Custom::MSSQLSchema",
            "Create",
            None,
            {
                "Name": self.name,
                "Owner": self.owner,
                "Server": {
                    "URL": "mssql://localhost:1444/master",
                    "Password": "P@ssW0rd",
                },
            },
        )

        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])
        self.assert_schema_and_owner(self.name, self.owner)

    def test_rename_failed(self):
        request = Request(
            "Custom::MSSQLSchema",
            "Create",
            None,
            {
                "Name": self.name,
                "Owner": self.owner,
                "Server": {
                    "URL": "mssql://localhost:1444/master",
                    "Password": "P@ssW0rd",
                },
            },
        )

        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])
        self.assert_schema_and_owner(self.name, self.owner)

        request.set_property("Name", random_name())
        request.physical_resource_id = response["PhysicalResourceId"]
        request.request_type = "Update"

        response = self.handle(request)
        self.assertEqual("FAILED", response["Status"], response["Reason"])
        self.assertEqual("schema name cannot be changed", response["Reason"])
        self.assert_schema_and_owner(self.name, self.owner)

    def test_change_owner(self):
        request = Request(
            "Custom::MSSQLSchema",
            "Create",
            None,
            {
                "Name": self.name,
                "Owner": self.owner,
                "Server": {
                    "URL": "mssql://localhost:1444/master",
                    "Password": "P@ssW0rd",
                },
            },
        )

        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])
        self.assert_schema_and_owner(self.name, self.owner)

        self.new_login_and_user(f"{self.owner}2")
        try:
            request.set_property("Owner", f"{self.owner}2")
            request.physical_resource_id = response["PhysicalResourceId"]
            request.request_type = "Update"

            response = self.handle(request)
            self.assertEqual("SUCCESS", response["Status"], response["Reason"])
            self.assert_schema_and_owner(self.name, f"{self.owner}2")
        finally:
            self.drop_login_and_user(f"{self.owner}2")
