from urllib.parse import quote_plus, unquote_plus

import lambda_views
from lambda_helper import *
from session_dynamodb import DynamoDbSessionInterface

Session = DynamoDbSessionInterface(DYNAMODB_SESSIONS_TABLE)


def lambda_handler(event, context):
    print(event)
    try:
        # parse the request
        request = parse_request(event)

        # extract values
        path = request['path']
        method = request['method']
        cookies = request['cookies']
        qs_data = request['query_data']

        # read or create session
        session = Session.open(cookies.get(SESSION_COOKIE_NAME))

        # auth path handlers
        if method == 'GET':

            if path == '/favicon.ico':
                # prevent a session being saved just for favicon requests
                return {'statusCode': 404}

            if path == LOGIN_PATH:
                session.create({'referer': unquote_plus(qs_data.get('referer', '/'))}).save()
                redirect_uri = request['url'] + LOGIN_CALLBACK
                return redirect(build_auth_url(session.session_id, SCOPE, redirect_uri), headers={
                    "Set-Cookie": f"{SESSION_COOKIE_NAME}={session.session_id};path=/",
                })

            elif path == LOGIN_CALLBACK:
                if qs_data.get('state') != session.session_id:  # mismatched session id
                    if request['querystring']: request['path'] += f"?{request['querystring']}"
                    return redirect(f"{LOGIN_PATH}?referer={quote_plus(request['path'])}")
                if "error" in qs_data:  # Authentication/Authorization failure
                    return response(render_template("auth_error.html", result=qs_data), headers={
                        'Content-Type': "text/html"
                    }, code=401)
                if qs_data.get('code'):
                    cache = load_cache(session.data)
                    result = build_msal_app(cache).acquire_token_by_authorization_code(
                        qs_data['code'],
                        scopes=SCOPE,  # Misspelled scope would cause an HTTP 400 error here
                        redirect_uri=request['url'] + LOGIN_CALLBACK)
                    if "error" in result:
                        return response(render_template("auth_error.html", result=result), headers={
                            'Content-Type': "text/html"
                        }, code=401)
                    session.session_state = qs_data.get('session_state')  # used by AAD single-sign-out
                    session.data["user"] = result.get("id_token_claims")
                    if cache.has_state_changed:
                        session.data["token_cache"] = cache.serialize()
                    session.save()
                    return redirect(session.data.get('referer', '/'))

            elif path == LOGOUT_PATH:
                post_logout_redirect_uri = quote_plus(request['url'] + LOGOUT_COMPLETE)
                return redirect(f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={post_logout_redirect_uri}")

            elif path == LOGOUT_CALLBACK:
                if 'sid' in qs_data:
                    session.delete_sid(qs_data['sid'])
                if SESSION_COOKIE_NAME in cookies:
                    session.delete()
                return {'statusCode': 200}

            elif path == LOGOUT_COMPLETE:
                return response(render_template("logged_out.html"), headers={
                    'Content-Type': "text/html",
                    "Set-Cookie": f"{SESSION_COOKIE_NAME}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/"
                })

        # simple authorized test
        if not session.data.get('user'):
            if request['querystring']: request['path'] += f"?{request['querystring']}"
            return redirect(f"{LOGIN_PATH}?referer={quote_plus(request['path'])}")

        # logged in, continue to your app
        return lambda_views.router(request, session)

    except UserWarning as e:
        print(str(e))
        return response(str(e), code=400)

    except Exception as e:
        print(str(e))
        return response(str(e), code=500)
