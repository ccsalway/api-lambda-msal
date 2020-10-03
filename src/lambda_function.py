from urllib.parse import quote_plus, unquote_plus
from request_helper import *
from response_helper import *
from session_dynamodb import DynamoDbSessionInterface
from views import load_module


def lambda_handler(event, context):
    # create a response object with the RequestId assigned for request tracking
    response = {'id': context.aws_request_id}
    try:
        # parse the request
        request = parse_request(event, context)
        # print(request)  # may contain secret data

        # extract values
        path = request['path']
        method = request['method']
        cookies = request['cookies']
        qs_data = request['query_data']

        # log request
        print(json.dumps({'RequestId': request['id'], 'Method': method, 'Path': path, 'SourceIP': request['source_ip']}))

        # add accept-encoding for compression decision later
        response['accept-encoding'] = request['headers'].get('accept-encoding', '')

        # initialise a session
        session = DynamoDbSessionInterface(DYNAMODB_SESSIONS_TABLE)

        # auth path handlers
        if method == 'GET':

            if path == '/favicon.ico':
                return serve_file(response, '/static/favicon.ico')

            if path == LOGIN_PATH:
                session.create({
                    'source_ip': request['source_ip'],
                    'referer': unquote_plus(qs_data.get('referer', '/'))
                }).save()
                redirect_uri = request['url'] + LOGIN_CALLBACK
                return redirect(response, build_auth_url(session.session_id, SCOPE, redirect_uri), headers={
                    "Set-Cookie": f"{SESSION_COOKIE_NAME}={session.session_id};path=/;SameSite=Lax;Secure",
                })

            elif path == LOGIN_CALLBACK:
                session.open(cookies.get(SESSION_COOKIE_NAME))
                if qs_data.get('state') != session.session_id:  # possible session forgery
                    return redirect(response, LOGIN_PATH)
                if "error" in qs_data:  # Authentication/Authorization failure
                    return format_response(response, render_template("auth_error.html", result=qs_data), code=401)
                if qs_data.get('code'):
                    cache = load_cache(session.data)
                    result = build_msal_app(cache).acquire_token_by_authorization_code(
                        qs_data['code'],
                        scopes=SCOPE,  # Misspelled scope would cause an HTTP 400 error here
                        redirect_uri=request['url'] + LOGIN_CALLBACK)
                    if "error" in result:
                        return format_response(response, render_template("auth_error.html", result=result), code=401)
                    session.session_state = qs_data.get('session_state')  # used by AAD single-sign-out
                    session.data["user"] = result.get("id_token_claims")
                    if cache.has_state_changed:
                        session.data["token_cache"] = cache.serialize()
                    session.save()
                    return redirect(response, session.data.get('referer', '/'))
                # invalid callback, redirect to login
                return redirect(response, LOGIN_PATH)

            elif path == LOGOUT_PATH:
                post_logout_redirect_uri = quote_plus(request['url'] + LOGOUT_COMPLETE)
                return redirect(response, f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={post_logout_redirect_uri}")

            elif path == LOGOUT_CALLBACK:
                if 'sid' in qs_data:
                    session.delete_sid(qs_data['sid'])
                if SESSION_COOKIE_NAME in cookies:
                    session.delete(cookies[SESSION_COOKIE_NAME])
                return format_response(response, code=204)

            elif path == LOGOUT_COMPLETE:
                return format_response(response, render_template("auth_logged_out.html"), headers={
                    "Set-Cookie": f"{SESSION_COOKIE_NAME}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;SameSite=None;Secure"
                })

        # simple authorisation test
        session.open(cookies.get(SESSION_COOKIE_NAME))
        if not session.data.get('user'):
            if request['querystring']: request['path'] += f"?{request['querystring']}"
            return redirect(response, f"{LOGIN_PATH}?referer={quote_plus(request['path'])}")

        # serve static files
        if method == 'GET' and path.startswith(STATIC_PATH):
            return serve_file(response, path)

        # path mapping to view
        f = VIEWS_PATH
        for p in path.split('/')[1:]:  # first is always blank
            if not p: continue
            f += '/' + p
            if os.path.isdir(cwd + f):  # directories take precedence
                continue
            if os.path.isfile(cwd + f + '.py'):
                return load_module(f, request, response, session)
        else:
            f += '/' + DEFAULT_VIEW
            if os.path.isfile(cwd + f + '.py'):
                return load_module(f, request, response, session)

        return format_response(response, "Page Not Found", code=404)

    except UserWarning as e:
        return format_response(response, str(e), code=400)

    except Exception as e:
        print(str(e))
        return format_response(response, "An error occurred. Check the logs.", code=500)
