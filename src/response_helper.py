import datetime
import decimal
import gzip
import json
from base64 import b64encode
from mimetypes import guess_type
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import *

jinja = Environment(
    loader=FileSystemLoader(cwd + TEMPLATES_PATH),
    autoescape=select_autoescape(['html'])
)


def json_serialize(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def render_template(template: str, **params):
    return jinja.get_template(template).render(params)


def compress_content(content: bytes, content_type: str):
    if content and content_type.startswith('text') or content_type in (
            "application/json",
            "application/xml",
            "application/xhtml+xml",
            "application/rss+xml",
            "application/javascript",
            "application/x-javascript",
    ):
        return gzip.compress(content)
    return None


def format_response(response: dict, body: str = '', is_base64_encoded: bool = False, headers: dict = None, code: int = 200):
    # response = {'id': <string>}
    if code == 204: body = ''  # no content
    if headers is None: headers = {}
    content_type = headers.get('Content-Type', 'text/html')
    if 'gzip' in response.get('accept-encoding', ''):
        gzipped = compress_content(body.encode('utf-8'), content_type)
        if gzipped:
            headers['Content-Encoding'] = 'gzip'
            body = b64encode(gzipped).decode('utf-8')
            content_type += '; charset=utf-8'
            is_base64_encoded = True
    response.update({
        'statusCode': code,
        'headers': {
            'Access-Control-Allow-Origin': "*",
            'Content-Type': content_type,
            **headers  # case sensitive key update
        },
        'body': body,
        'isBase64Encoded': is_base64_encoded
    })
    # DO NOT log the Location header as it may contain secret data such as clientId and sessionToken
    # DO NOT log the body when status is 2xx as it may contain secret data such as form data
    content = '<content hidden>' if body and code < 400 else body
    print(json.dumps({'RequestId': response['id'], 'Status': code, 'Content': content}))
    return response


def response_json(response: dict, body: dict, headers: dict = None, code: int = 200):
    if headers is None: headers = {}
    return format_response(
        response,
        headers={'Content-Type': "application/json", **headers},
        body=json.dumps(body, default=json_serialize),
        code=code,
    )


def redirect(response: dict, url: str, headers: dict = None, code: int = 302):
    if headers is None: headers = {}
    return format_response(
        response,
        headers={'Location': url, **headers},
        code=code,
    )


def serve_file(response: dict, path: str):
    """ This is not designed for large files, which should be served from S3 with signed URL's. """
    fullpath = cwd + path
    if not os.path.isfile(fullpath):
        return format_response(response, 'File Not Found', code=404)
    # Content Type
    content_type, encoding = guess_type(fullpath)
    if not content_type:
        content_type = "application/octet-stream"
    # Content Length
    content_length = os.path.getsize(fullpath)  # bytes
    # Content
    with open(fullpath, 'rb') as f:
        content = f.read()
    # Compress
    encoding_header = {}
    if 'gzip' in response.get('accept-encoding', ''):
        gzipped = compress_content(content, content_type)
        if gzipped:
            content = gzipped
            content_type += f'; charset={encoding or "utf-8"}'
            encoding_header = {'Content-Encoding': 'gzip'}
    # build response
    response.update({
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': "*",
            'Content-Type': content_type,
            'Content-Length': content_length,
            **encoding_header
        },
        'body': b64encode(content).decode("utf-8"),
        'isBase64Encoded': True
    })
    print(json.dumps({'RequestId': response['id'], 'Status': 200, 'File': fullpath, 'Content-Type': content_type, 'Content-Length': content_length}))
    return response
