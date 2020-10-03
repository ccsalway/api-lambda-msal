import datetime
import decimal
import json
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


def response(body: str = '', is_base64_encoded: bool = False, headers: dict = None, code: int = 200):
    if headers is None: headers = {}
    resp = {
        'statusCode': code,
        'headers': {
            'Access-Control-Allow-Origin': "*",
            'Content-Type': 'text/html',
            **headers  # case sensitive key update
        },
        'body': body,
        'isBase64Encoded': is_base64_encoded
    }
    if code != 200: print(resp)  # may contain secret data
    return resp


def response_json(body: dict, headers: dict = None, code: int = 200):
    if headers is None: headers = {}
    return response(
        code=code,
        body=json.dumps(body, default=json_serialize),
        headers={'Content-Type': "application/json", **headers}
    )


def redirect(url: str, headers: dict = None, code: int = 302):
    if headers is None: headers = {}
    return response(
        code=code,
        headers={'Location': url, **headers}
    )


def serve_file(path: str):
    """ This is not designed for large files, which should be served from S3 with signed URL's. """
    if not os.path.isfile(path):
        return response('File Not Found', code=404)
    # Content Type
    content_type, enc = guess_type(path)
    if not content_type:
        content_type = "application/octet-stream"
    # Content Length
    content_length = os.path.getsize(path)
    # Content
    with open(path, 'rb') as f:
        content = f.read()
    return response(
        headers={
            'Content-Type': content_type,
            'Content-Length': content_length
        },
        body=b64encode(content).decode('utf-8'),
        is_base64_encoded=True
    )
