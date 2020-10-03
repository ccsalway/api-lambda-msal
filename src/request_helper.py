import re
from base64 import b64decode
from json import loads, JSONDecodeError
from urllib.parse import parse_qsl, urlencode
import msal
from config import *


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
    url = f"{headers.get('x-forwarded-proto', 'https')}://{request['domainName']}:{headers.get('x-forwarded-port', 443)}"

    # get source ip
    source_ip = headers.get('x-forwarded-for', '').split(',')[0].strip()  # Syntax: <client>, <proxy1>, <proxy2>

    # get version
    version = event.get('version', '1.0')

    # get stage
    stage = '' if request['stage'] == '$default' else request['stage']

    # get path, method and cookies
    if version == '1.0':
        path = event['path'] if not stage else event['path'].replace(f"/{stage}", '', 1) or '/'
        method = event['httpMethod']
        cookies = {k: v for k, v in (c.strip().split('=', 1) for c in headers.get('cookie', '').split(';'))}
        if not source_ip: source_ip = request['identity']['sourceIp']
    elif version == '2.0':
        path = event['rawPath'] if not stage else event['rawPath'].replace(f"/{stage}", '', 1) or '/'
        method = request['http']['method']
        cookies = {k: v for k, v in (c.split('=', 1) for c in event.get('cookies', []))}
        if not source_ip: source_ip = request['http']['sourceIp']
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
        content_type = headers.get('content-type', '')
        # application/json
        if content_type.lower().startswith('application/json'):
            try:
                form_data = loads(body)
            except JSONDecodeError as e:
                raise UserWarning(str(e))
        # x-www-form-urlencoded
        elif content_type.lower().startswith('application/x-www-form-urlencoded'):
            form_data = {k: v for k, v in parse_qsl(body)}
        # multipart/form-data
        elif content_type.lower().startswith('multipart/form-data'):
            m = re.search(r'boundary=("[^"]+"|[^ ]+)', content_type, flags=re.IGNORECASE)
            if m is not None:
                boundary = m.group(1).strip('" ')
                for b in ('\r\n' + body).split('\r\n--' + boundary):
                    if not b or b.startswith('--'): continue
                    h, c = b.split('\r\n' * 2, 1)  # boundary: header, content
                    hk, hv = h.split(':', 1)  # header: key, value
                    if not hk.lower().startswith('\r\ncontent-disposition'):
                        continue
                    if not hv.lstrip().lower().startswith('form-data'):
                        continue
                    lines = hv.split('\r\n')  # a file can have its content-type on the next line
                    f = {k.strip().lower(): v.strip('" ') for k, v in (d.split('=', 1) for d in lines[0].split(';') if '=' in d)}
                    if 'name' not in f:  # we need a name for the form item
                        continue
                    if 'filename' not in f:  # form field
                        form_data[f['name']] = c
                    else:
                        ct = 'application/octet-stream'
                        if len(lines) > 1 and lines[1].lower().startswith('content-type'):
                            _, ct = lines[1].split(':', 1)
                        form_data[f['name']] = {'filename': f['filename'], 'mimetype': ct.strip(), 'content': c}

    return {
        'event': event, 'stage': stage, 'source_ip': source_ip,
        'url': url, 'path': path, 'method': method, 'headers': headers,
        'cookies': cookies, 'form_data': form_data, 'query_data': query_data,
        'querystring': querystring,
    }
