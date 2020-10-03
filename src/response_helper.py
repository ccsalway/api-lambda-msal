import datetime
import decimal
import json
import gzip
from base64 import b64encode
from mimetypes import guess_type
from jinja2 import Environment, PackageLoader, select_autoescape
from config import *

jinja = Environment(
    loader=PackageLoader(__name__),
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


def response(body: str = '', compress: bool = False, is_base64_encoded: bool = False, headers: dict = None, code: int = 200):
    if headers is None: headers = {}
    content_type = headers.get('Content-Type', 'text/html')
    if compress:
        gzipped = compress_content(body.encode('utf-8'), content_type)
        if gzipped:
            headers['Content-Encoding'] = 'gzip'
            body = b64encode(gzipped).decode('utf-8')
            content_type += '; charset=utf-8'
            is_base64_encoded = True
    resp = {
        'statusCode': code,
        'headers': {
            'Access-Control-Allow-Origin': "*",
            'Content-Type': content_type,
            **headers  # case sensitive key update
        },
        'body': body,
        'isBase64Encoded': is_base64_encoded
    }
    # print(resp)  # may contain secret data
    return resp


def response_json(body: dict, compress: bool = False, headers: dict = None, code: int = 200):
    if headers is None: headers = {}
    return response(
        code=code,
        headers={
            'Content-Type': "application/json",
            **headers
        },
        body=json.dumps(body, default=json_serialize),
        compress=compress
    )


def redirect(url: str, headers: dict = None, code: int = 302):
    if headers is None: headers = {}
    return response(
        code=code,
        headers={'Location': url, **headers}
    )


def serve_file(path: str, compress: bool = False):
    """ This is not designed for large files, which should be served from S3 with signed URL's. """
    if not os.path.isfile(path):
        return response('File Not Found', code=404)
    # Content Type
    content_type, encoding = guess_type(path)
    if not content_type:
        content_type = "application/octet-stream"
    # Content Length
    content_length = os.path.getsize(path)  # bytes
    # Content
    with open(path, 'rb') as f:
        content = f.read()
    # Compress
    encoding_header = {}
    if compress:
        gzipped = compress_content(content, content_type)
        if gzipped:
            content = gzipped
            content_type += f'; charset={encoding or "utf-8"}'
            encoding_header = {'Content-Encoding': 'gzip'}
    # return file
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': "*",
            'Content-Type': content_type,
            'Content-Length': content_length,
            **encoding_header
        },
        'body': b64encode(content).decode('utf-8'),
        'isBase64Encoded': True
    }
