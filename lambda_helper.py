import datetime
import json
from base64 import b64decode
from urllib.parse import parse_qsl, urlencode

import msal
from jinja2 import Environment, PackageLoader, select_autoescape

from config import *

jinja = Environment(
    loader=PackageLoader(__name__),
    autoescape=select_autoescape(['html'])
)


# Helper functions
def render_template(template: str, **params):
    return jinja.get_template(template).render(params)


def json_serialize(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


# MSAL functions
def load_cache(data):
    cache = msal.SerializableTokenCache()
    if data.get("token_cache"):
        cache.deserialize(data["token_cache"])
    return cache


def build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY,
        client_credential=CLIENT_SECRET, token_cache=cache)


def build_auth_url(state: str, scopes: list, redirect_uri: str):
    return build_msal_app().get_authorization_request_url(
        scopes, state=state, redirect_uri=redirect_uri)


# API functions
def parse_request(event):
    # ref: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html

    # assign request context
    request = event['requestContext']

    # standardize header keys to lower case
    headers = {k.lower(): v for k, v in event.get('headers', {}).items()}

    # build url
    url = f"{headers.get('x-forwarded-proto')}://{request['domainName']}:{headers.get('x-forwarded-port')}"

    # get version
    version = event.get('version', '1.0')

    # get stage
    stage = '' if request['stage'] == '$default' else request['stage']

    # get path, method and cookies
    if version == '1.0':
        path = event['path'] if not stage else event['path'].replace(f"/{stage}", '', 1) or '/'
        method = event['httpMethod']
        cookies = {k: v for k, v in (c.strip().split('=', 1) for c in headers.get('cookie', '').split(';'))}
    elif version == '2.0':
        path = event['rawPath'] if not stage else event['rawPath'].replace(f"/{stage}", '', 1) or '/'
        method = request['http']['method']
        cookies = {k: v for k, v in (c.split('=', 1) for c in event.get('cookies', []))}
    else:
        raise Exception(f"Unhandled version: {version}")

    # get querystring parameters
    query_data = event.get('queryStringParameters')
    if query_data is None: query_data = {}
    querystring = urlencode(query_data)

    # get form data
    form_data = {}
    if event.get('body') is not None:
        body = event['body']
        if event.get('isBase64Encoded', False):
            body = b64decode(body.encode('utf-8')).decode('utf-8')
        if headers.get('content-type', '').lower().startswith('application/x-www-form-urlencoded'):
            form_data = {k: v for k, v in parse_qsl(body)}
        # TODO: support multipart/form-data

    # return data
    return {
        'event': event,
        'stage': stage,
        'url': url,
        'path': path,
        'method': method,
        'headers': headers,
        'cookies': cookies,
        'form_data': form_data,
        'query_data': query_data,
        'querystring': querystring
    }


def response(body=None, headers: dict = None, code: int = 200):
    if headers is None: headers = {}
    resp = {
        'statusCode': code,
        'headers': {
            'Access-Control-Allow-Origin': "*",
            'Content-Type': "application/json" if isinstance(body, dict) else "text/plain",
            **headers  # case sensitive key update
        },
        'body': json.dumps(body, default=json_serialize) if isinstance(body, dict) else body or '',
        'isBase64Encoded': False
    }
    print(resp)
    return resp


def redirect(url: str, headers: dict = None, code: int = 302):
    if headers is None: headers = {}
    resp = {
        'statusCode': code,
        'headers': {
            'Access-Control-Allow-Origin': "*",
            'Location': url,
            **headers  # case sensitive key update
        }
    }
    print(resp)
    return resp
