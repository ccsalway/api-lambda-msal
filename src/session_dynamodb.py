"""
aws dynamodb create-table --table-name lambda_sessions \
    --attribute-definitions AttributeName=id,AttributeType=S AttributeName=sid,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --provisioned-throughput "ReadCapacityUnits=5,WriteCapacityUnits=5" \
    --global-secondary-indexes "IndexName=sid-index,KeySchema=[{AttributeName=sid,KeyType=HASH}],Projection={ProjectionType=KEYS_ONLY},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}"
aws dynamodb update-time-to-live --table-name lambda_sessions \
    --time-to-live-specification 'Enabled=true,AttributeName=ttl'
"""
import datetime
import decimal
import json
from os import urandom
from time import time

from boto3 import client
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

serializer = TypeSerializer()
deserializer = TypeDeserializer()

ddb = client('dynamodb')


class DynamoDbSessionInterface:

    def __init__(self, table: str = 'lambda_sessions', sid_index_name: str = 'sid-index'):
        self.table = table
        self.sid_index_name = sid_index_name

    def _json_serialize(self, o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        return str(o)

    def _generate_id(self):
        # your session is only as secure as your cookie so make it long
        return urandom(64).hex()

    def clear(self):
        self.session_id = None
        self.session_state = 'null'
        self.data = {}
        return self

    def create(self, data: dict = None):
        if data is None: data = {}
        self.session_id = self._generate_id()  # assigned to the users cookie
        self.session_state = 'null'  # a reference to the users session in Azure
        self.data = data
        return self

    def open(self, session_id: str = None):
        if session_id:
            response = ddb.get_item(
                TableName=self.table,
                Key={"id": {"S": session_id}}
            )
            if 'Item' in response:
                item = {k: deserializer.deserialize(v) for k, v in response['Item'].items()}
                self.item = item
                self.session_id = item['id']
                self.session_state = item['sid']
                self.data = item['data']
                return self
        return self.create()

    def save(self, ttl: int = 3600):
        now = int(time())  # epoch
        payload = {
            'id': self.session_id,
            'sid': self.session_state,
            'modified': now,
            'ttl': now + ttl,
            'data': self.data
        }
        ddb.put_item(
            TableName=self.table,
            Item={k: serializer.serialize(v) for k, v in payload.items()}
        )
        return self

    def delete(self, session_id: str = None):
        if session_id:
            ddb.delete_item(
                TableName=self.table,
                Key={"id": {"S": session_id}}
            )
        elif self.session_id:
            ddb.delete_item(
                TableName=self.table,
                Key={"id": {"S": self.session_id}}
            )
        return self.clear()

    def delete_sid(self, sid: str):
        # When a user signs out of Azure (Single-Sign-Out), Azure sends a request to this app to
        # remove the users session. The request contains the querystring '?sid=<string>' which
        # matches the value from '?session_state=<string>' sent by Azure when logging in to this app.
        response = ddb.query(
            TableName=self.table,
            IndexName=self.sid_index_name,
            KeyConditionExpression='sid=:sid',
            ExpressionAttributeValues={":sid": {"S": sid}})
        if response['Count'] > 0:
            for item in response['Items']:
                item = {k: deserializer.deserialize(v) for k, v in item.items()}
                ddb.delete_item(
                    TableName=self.table,
                    Key={"id": {"S": item['id']}}
                )

    def get(self):
        return {
            'id': self.session_id,
            'sid': self.session_state,
            'data': self.data
        }

    def __str__(self):
        return json.dumps(self.get(), default=self._json_serialize)
