import uuid
import json
import logging
from typing import Union
from unittest import TestCase
from cfn_resource_provider import ResourceProvider
import sqlserver_resource_providers


class Request:
    def __init__(
        self,
        resource_type: str,
        request_type: str,
        logical_resource_id=None,
        properties: dict = {},
    ):
        self.request = {
            "RequestType": request_type,
            "ResponseURL": "https://dev/null",
            "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
            "RequestId": "request-%s" % str(uuid.uuid4()),
            "ResourceType": resource_type,
            "LogicalResourceId": logical_resource_id
            if logical_resource_id
            else "TestResource",
            "ResourceProperties": json.loads(json.dumps(properties)),
            "OldResourceProperties": {},
        }

    @property
    def request_type(self) -> str:
        return self.request["RequestType"]

    @request_type.setter
    def request_type(self, value: str):
        self.request["RequestType"] = value

    @property
    def resource_properties(self):
        return self.request["ResourceProperties"]

    @resource_properties.setter
    def resource_properties(self, properties: dict):
        self.request["ResourceProperties"] = properties

    @property
    def old_resource_properties(self):
        return self.request["OldResourceProperties"]

    @old_resource_properties.setter
    def old_resource_properties(self, properties: dict):
        self.request["OldResourceProperties"] = properties

    @property
    def response_url(self) -> str:
        return self.request["ResponseURL"]

    @response_url.setter
    def response_url(self, url: str):
        self.request["ResponseURL"] = url

    def as_dict(self) -> dict:
        return json.loads(json.dumps(self.request))


class CloudformationCustomProviderTestCase(TestCase):
    def __init__(self, tests):
        super(CloudformationCustomProviderTestCase, self).__init__(tests)
        self.objects = {}
        self.cleanup = {}
        self.provider: ResourceProvider = None

    def success(self):
        return self.provider.response and self.provider.response.status == "SUCCESS"

    @property
    def request(self):
        return self.provider.request

    @property
    def response(self):
        return self.provider.response

    @property
    def provider(self):
        return self._provider

    @provider.setter
    def provider(self, provider: ResourceProvider):
        self._provider = provider
        if provider:
            self._provider.send_response = self._receive_response

    def _receive_response(self):
        self._received_response = json.loads(json.dumps(self.provider.response))

    def handle(self, request: Union[Request, dict]) -> dict:

        self._received_response = None
        if isinstance(request, Request):
            request = request.as_dict()

        if request["RequestType"] == "Create":
            response = self.provider.handle(request, {})
            if response["Status"] == "SUCCESS":
                physical_resource_id = response["PhysicalResourceId"]
                self.objects[physical_resource_id] = json.loads(json.dumps(request))

        elif request["RequestType"] == "Delete":
            physical_resource_id = request["PhysicalResourceId"]
            response = self.provider.handle(request, {})
            if response["Status"] == "SUCCESS" and physical_resource_id in self.objects:
                del self.objects[physical_resource_id]

        elif request["RequestType"] == "Update":
            physical_resource_id = request["PhysicalResourceId"]
            exists = physical_resource_id in self.objects
            assert exists
            request["OldResourceProperties"] = json.loads(
                json.dumps(self.objects[physical_resource_id]["ResourceProperties"])
            )
            response = self.provider.handle(request, {})
            if response["Status"] == "SUCCESS":
                if response["PhysicalResourceId"] != physical_resource_id:
                    self.objects[response["PhysicalResourceId"]] = json.loads(
                        json.dumps(request)
                    )
        else:
            assert False, f"invalid request type {request['RequestType']}"

        return response

    def delete_resource(self, physical_resource_id: str) -> str:
        if physical_resource_id not in self.objects:
            return f"resource {physical_resource_id} not found"

        error = None
        request = self.provider.request
        response = self.provider.response
        try:
            delete_request = json.loads(json.dumps(self.objects[physical_resource_id]))
            delete_request["PhysicalResourceId"] = physical_resource_id
            delete_request["RequestType"] = "Delete"
            delete_response = self.provider.handle(delete_request, {})
            if delete_response["Status"] != "SUCCESS":
                error = delete_response["Reason"]
            del self.objects[physical_resource_id]
        finally:
            self.provider.request = request
            self.provider.response = response

        return error

    def delete_all_created_resources(self) -> bool:
        success = True
        for physical_resource_id in list(self.objects.keys()):
            logging.info("deleeting %s", physical_resource_id)
            request = self.objects[physical_resource_id]
            if request["RequestType"] != "Delete":
                error = self.delete_resource(physical_resource_id)
                success = success and not error
                if error:
                    logging.error(
                        "failed to delete %s, %s", physical_resource_id, error
                    )
        return success

    def setUp(self) -> None:
        self.provider = sqlserver_resource_providers.login.SQLServerLogin()

    def tearDown(self) -> None:
        if self.provider:
            ok = self.delete_all_created_resources()
            self.assertTrue(ok, "could not delete all created resources")

    def test_create_login(self):
        request = Request(
            "Custom::SQLServerLogin",
            "Create",
            None,
            {
                "LoginName": "balbalba1",
                "Password": "G3he1m!!Echh",
                "Server": {
                    "URL": "sqlserver://localhost:1444/master",
                    "Password": "P@ssW0rd",
                },
            },
        )
        response = self.handle(request)
        self.assertEqual("SUCCESS", response["Status"], response["Reason"])
