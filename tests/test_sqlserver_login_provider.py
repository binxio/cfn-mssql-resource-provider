import sys
import random, string
import re
import uuid
import pymssql
import boto3
import logging
from hashlib import md5
from sqlserver_resource_providers import handler
from sqlserver_resource_providers.connection_info import from_url
from unittest import TestCase

logging.basicConfig(level=logging.INFO)


def random_user():
    chars = string.ascii_letters
    return "".join(random.choice(chars) for i in range(20))


def random_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(random.choice(chars) for i in range(20))


class Event(dict):
    def __init__(self, request_type, login_name, physical_resource_id=None):
        self.update(
            {
                "RequestType": request_type,
                "ResponseURL": "https://httpbin.org/put",
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "RequestId": "request-%s" % str(uuid.uuid4()),
                "ResourceType": "Custom::SQLServerLogin",
                "LogicalResourceId": "Whatever",
                "OldResourceProperties": {},
                "ResourceProperties": {
                    "LoginName": login_name,
                    "Password": random_password(),
                    "Server": {
                        "URL": "sqlserver://localhost:1444",
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

    def test_user_connection(self, password=None):
        p = self["ResourceProperties"]
        if password is None:
            password = p["Password"]
        args = from_url(p["Server"]["URL"], password)
        args["user"] = p["LoginName"]
        args["password"] = password
        return pymssql.connect(**args)


class SQLServerLoginTestCase(TestCase):
    def setUp(self) -> None:
        with Event("Create", "ladila").test_owner_connection() as c:
            c.autocommit(True)
            with c.cursor() as c:
                c.execute(
                    """
                    IF NOT EXISTS(SELECT * FROM sys.databases WHERE name = 'alt_db')
                    BEGIN
                        CREATE DATABASE [alt_db]
                    END
                    """
                )

    def test_invalid_login_name(self):
        event = Event("Create", "nicey-nice] ; drop user [blalba")
        response = handler(event, {})
        assert response["Status"] == "FAILED", response["Reason"]

    def test_password_with_special_chars(self):
        name = random_user()
        event = Event("Create", name)
        event["ResourceProperties"]["Password"] = "AtL3@srabd'\\efg~"
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        with event.test_user_connection() as connection:
            pass

        assert "PhysicalResourceId" in response
        physical_resource_id = response["PhysicalResourceId"]

        # delete the created login
        event = Event("Delete", name, physical_resource_id)
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

    def test_create_login(self):
        # create a test login
        name = random_user()
        event = Event("Create", name)
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        assert "PhysicalResourceId" in response
        physical_resource_id = response["PhysicalResourceId"]
        assert re.match(r"^sqlserver:[^:]+:login:[0-9]+$", physical_resource_id)

        try:
            with event.test_user_connection() as connection:
                pass
        except Exception as error:
            p = event["ResourceProperties"]
            raise error

        event = Event("Create", name)
        response = handler(event, {})
        assert response["Status"] == "FAILED", "%s" % response["Reason"]
        assert "already exists." in response["Reason"]

        # delete non existing login
        event = Event("Delete", name + "-", physical_resource_id + "-")
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        # delete the created login
        event = Event("Delete", name, physical_resource_id)
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        try:
            with event.test_user_connection() as connection:
                assert False, "succesfully logged in to deleted login"
        except:
            pass

        event = Event("Delete", name, physical_resource_id)
        event["ResourceProperties"]["DeletionPolicy"] = "Drop"
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        try:
            with event.test_user_connection() as connection:
                assert False, "login not dropped"
        except Exception as error:
            pass

    def test_all_updates(self):
        # create a test login
        name = "u%s" % str(uuid.uuid4()).replace("-", "")
        event = Event("Create", name)
        event["DeletionPolicy"] = "Drop"
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", "%s" % response["Reason"]
        assert "PhysicalResourceId" in response
        physical_resource_id = response["PhysicalResourceId"]
        assert re.match(r"^sqlserver:[^:]+:login:[0-9]+$", physical_resource_id)

        # update the password
        event = Event("Update", name, physical_resource_id)
        event["Password"] = "geheim"
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        with event.test_user_connection():
            pass

        # Rename the login
        event = Event("Update", name + "2", physical_resource_id)
        event["OldResourceProperties"]["LoginName"] = name

        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]
        physical_resource_id_2 = response["PhysicalResourceId"]

        assert re.match(r"^sqlserver:[^:]+:login:[0-9]+$", physical_resource_id_2)
        assert physical_resource_id_2 == physical_resource_id

        with event.test_user_connection():
            pass

        ## change default database
        event = Event("Update", name + "2", physical_resource_id)
        event["ResourceProperties"]["DefaultDatabase"] = "alt_db"
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

        with event.test_user_connection():
            pass

        # delete login
        event = Event("Delete", name + "2", physical_resource_id)
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

    def test_invalid_delete(self):
        event = Event("Delete", "noop", "sqlserver:localhost:1444:noop")
        del event["ResourceProperties"]["LoginName"]
        response = handler(event, {})
        assert response["Status"] == "SUCCESS", response["Reason"]

    def test_password_parameter_use(self):
        ssm = boto3.client("ssm")
        uuid_string = str(uuid.uuid4()).replace("-", "")
        name = "user_%s" % uuid_string
        user_password_name = "p%s" % uuid_string
        dbowner_password_name = "o%s" % uuid_string
        try:
            event = Event("Create", name)

            user_password = str(uuid.uuid4())
            del event["ResourceProperties"]["Password"]
            event["ResourceProperties"]["PasswordParameterName"] = user_password_name

            dbowner_password = event["ResourceProperties"]["Server"]["Password"]
            del event["ResourceProperties"]["Server"]["Password"]
            event["ResourceProperties"]["Server"][
                "PasswordParameterName"
            ] = dbowner_password_name

            ssm.put_parameter(
                Name=user_password_name,
                Value=user_password,
                Type="SecureString",
                Overwrite=True,
            )
            ssm.put_parameter(
                Name=dbowner_password_name,
                Value=dbowner_password,
                Type="SecureString",
                Overwrite=True,
            )
            response = handler(event, {})

            with event.test_user_connection(user_password):
                pass

            event["PhysicalResourceId"] = response["PhysicalResourceId"]

            response = handler(event, {})
        except Exception as e:
            sys.stderr.write("%s\n" % e)
            raise
        finally:
            ssm.delete_parameter(Name=user_password_name)
            ssm.delete_parameter(Name=dbowner_password_name)
