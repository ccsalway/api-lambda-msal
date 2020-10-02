import os

# OIDC
AUTHORITY = os.environ['AUTHORITY']
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
SCOPE = []  # msal adds offline_access openid profile

# session
DYNAMODB_SESSIONS_TABLE = 'lambda_sessions'
SESSION_COOKIE_NAME = 'session'

# URLs
# - Register the base URL of this app in the AAD <app>/Branding/Home page URL,
#   then this app will be accessible on the 'My Apps' page for users to click.
LOGIN_PATH = '/auth/login'
LOGIN_CALLBACK = LOGIN_PATH + "/callback"  # register URL + this path with oauth app as redirect uri
LOGOUT_PATH = '/auth/logout'
LOGOUT_CALLBACK = LOGOUT_PATH + "/callback"  # register URL + this path with oauth app as logout url
LOGOUT_COMPLETE = LOGOUT_PATH + '/complete'
