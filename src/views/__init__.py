import sys
from config import DEFAULT_FUNC


def load_module(path, request, response, session):
    m = path.lstrip('/').replace('/', '.')
    __import__(m)
    return getattr(sys.modules[m], DEFAULT_FUNC)(request, response, session)
