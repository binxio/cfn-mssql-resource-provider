import logging
import random
import string

import pymssql

from cfn_resource_provider_test import CloudformationCustomProviderTestCase, Request
from mssql_resource_provider.grant import MSSQLDatabaseGrant

logging.basicConfig(level=logging.INFO)


def random_name():
    chars = string.ascii_letters
    return "".join(random.choice(chars) for i in range(20))


class MSSQLDatabaseGrantTestCase(CloudformationCustomProviderTestCase):
    def connect(self, database="master"):
        return pymssql.connect(
            server="localhost",
            user="sa",
            port=1444,
            database=database,
            password="P@ssW0rd",
        )

    def new_database(self, name) -> str:
        with self.connect() as connection:
            connection.autocommit(True)
            connection.cursor().execute(f"CREATE DATABASE [{name}]")
            connection.commit()

    def new_login_and_user(self, database, name) -> str:
        with self.connect(database) as connection:
            connection.cursor().execute(
                f"CREATE LOGIN [{name}] WITH PASSWORD = '{name}!'"
            )
            connection.cursor().execute(f"CREATE USER [{name}] FOR LOGIN [{name}]")
            connection.commit()

    def drop_database(self, name) -> str:
        with self.connect() as connection:
            connection.autocommit(True)
            connection.cursor().execute(f"DROP DATABASE [{name}];")

    def drop_login_and_user(self, database, name) -> str:
        with self.connect(database) as connection:
            try:
                connection.cursor().execute(f"DROP USER IF EXISTS [{name}]")
            except Exception as e:
                logging.info("drop user failed", e)
            try:
                connection.cursor().execute(f"DROP LOGIN [{name}]")
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

    def assert_permission(
        self, state: str, permission: str, username: str, database: str
    ):
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                    use {database}; 
                    SELECT * 
                    FROM sys.database_permissions
                    WHERE USER_NAME(grantee_principal_id) = '{username}'
                    AND permission_name = '{permission}'
                    AND state_desc = '{state}'
                """
            )
            cursor.fetchone()

    def setUp(self):
        super().setUp()
        self.provider = MSSQLDatabaseGrant()
        self.username = random_name()
        self.database = f"db_{self.username}"
        self.new_database(self.database)
        self.new_login_and_user(self.database, self.username)

    def tearDown(self) -> None:
        super().tearDown()
        self.drop_login_and_user(self.database, self.username)
        self.drop_database(self.database)

    def test_create(self):
        request = Request(
            "Custom::MSSQLDatabaseGrant",
            "Create",
            None,
            {
                "Permission": "ALL",
                "UserName": self.username,
                "Database": self.database,
                "Server": {
                    "URL": f"mssql://localhost:1444/{self.database}",
                    "Password": "P@ssW0rd",
                },
            },
        )
        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])

        self.assert_permission("GRANT", "ALL", self.username, self.database)

        # revoke the grant again
        request.request_type = "Delete"
        request.physical_resource_id = response["PhysicalResourceId"]
        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])
        self.assert_permission("REVOKE", "ALL", self.username, self.database)

    def test_update(self):
        request = Request(
            "Custom::MSSQLDatabaseGrant",
            "Create",
            None,
            {
                "Permission": "ALL",
                "UserName": self.username,
                "Database": self.database,
                "Server": {
                    "URL": f"mssql://localhost:1444/{self.database}",
                    "Password": "P@ssW0rd",
                },
            },
        )
        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])
        physical_resource_id = response["PhysicalResourceId"]

        self.assert_permission("GRANT", "ALL", self.username, self.database)

        # revoke the grant again
        request.request_type = "Update"
        request.physical_resource_id = physical_resource_id
        request.set_property("Permission", "SELECT")
        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])
        self.assertNotEqual(physical_resource_id, response["PhysicalResourceId"])

        self.assert_permission("GRANT", "CONNECT", self.username, self.database)
        self.assert_permission("GRANT", "SELECT", self.username, self.database)
