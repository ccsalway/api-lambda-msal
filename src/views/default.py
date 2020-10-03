import config
from response_helper import format_response, render_template


def view(request, response, session):
    user = session.data.get('user', {})
    return format_response(response, render_template('index.html', user=user, config=config))
