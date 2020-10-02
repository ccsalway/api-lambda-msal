# aws-api-lambda-msal
Base source code for creating a lambda application that sits behind AAD authentication using OIDC. 

# Process

1. Request Website
    - API forwards request payload to Lambda
    - Lambda handler parses the request extracting key parameters like querystring parameters, cookies, headers, etc
    - Checks for and, if exists, retrieves the `session` from DynamoDB using a session cookie as the ID
    - If session does not exist, redirects the user to the login page
        - creates a new session, storing the data in DynamoDB
        - redirects the users browser to the AAD login page whilst setting a cookie with the session ID
        - AAD logs the user in and returns the user back to the LOGIN_CALLBACK URL   
 

# Files

`lambda_function` - the entry point for the lambda and contains the authentication stages  
`lambda_helper` - contains functions to parse the request from 

## Setup in AAD

Create an application in Azure without a Redirect URI - you will add this later.  