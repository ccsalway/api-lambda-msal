import config
from response_helper import response, render_template, serve_file


def index(request, session):
    user = session.data.get('user', {})
    return response(render_template('index.html', user=user, config=config))


def router(request, session):
    """ This function is called after successful login """
    method = request['method']
    path = request['path']

    # path handlers
    if method == 'GET':

        # static files
        if path.startswith('/static'):
            return serve_file(f'{config.PWD}/{path}')

        # index page
        if path == '/' or path == '/index':
            return index(request, session)

    elif method == 'POST':
        pass

    # default
    return response("Page Not Found", code=404)
