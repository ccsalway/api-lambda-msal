import config
from response_helper import format_response, render_template, serve_file


def index(request, response, session):
    user = session.data.get('user', {})
    return format_response(response, render_template('index.html', user=user, config=config))


def router(request, response, session):
    """ This function is called after successful login """
    method = request['method']
    path = request['path']

    # path handlers
    if method == 'GET':

        # static files
        if path.startswith('/static'):
            return serve_file(response, path)

        # index page
        if path == '/' or path == '/index':
            return index(request, response, session)

    elif method == 'POST':
        pass

    # default
    return format_response(response, "Page Not Found", code=404)
