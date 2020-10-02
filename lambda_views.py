import config
from lambda_helper import response, render_template


def index(session):
    user = session.data.get('user', {})
    return response(render_template('index.html', user=user, config=config), headers={
        'Content-Type': 'text/html'
    })
