# aws-api-lambda-msal
Base source code for creating a lambda application that sits behind AAD authentication using OIDC. 

Acronyms: AAD - Azure Active Directory, DDB - DynamoDB

## Setup

- Ensure DDB table exists in the account you will deploy this lambda to - see below for DDB setup
- Fork this repo for your new webapp
- Create your views in `lambda_views.py` - see file for examples
- Create an AAD application without a `Redirect URI` - you will add this later  
- Publish your webapp lambda with the IAM permissions shown below and the following
 environment variables from the AAD application:
    - `AUTHORITY` - https://login.microsoftonline.com/[Directory (tenant) ID]
    - `CLIENT_ID` - [Application (client) ID]
    - `CLIENT_SECRET` - (you will need to create one in the app under Certificates & secrets)
- Create an AWS HTTP API Gateway (2.0) and route `ALL /{proxy+}` to the Lambda  
- Setup DNS if using it
- Update the following fields in the AAD application:
  - `Branding / Home page URL` - set to https://{domain name}
  - `Authentication / Redirect URI` - add https://{domain name}/auth/login/callback
  - `Authentication / Logout URL` - set to https://{domain name}/auth/logout/callback
  
  
## Process

### Login 
- API Gateway forwards request payload to Lambda
- Lambda handler parses the request, extracting key parameters like querystring, cookies, headers, etc
- Checks for and, if exists, retrieves session data from DDB using a session cookie as the ID
- If session does not exist, redirects the user to the login page, where it:
    - creates a new session, storing the data in DDB
    - redirects the user to the AAD login page whilst setting a session cookie
    - AAD logs in the user and returns the user back to the `LOGIN_CALLBACK URL`
    - login is checked, and if good, redirects the user to their initial request, else redirects to `LOGIN_PATH`
 - Once logged in, the work passes to `lambda_views.py` function `lambda_views.router(request, session)` for processing

### Logout
- User is directed to AAD logout process
- Once logged out, AAD makes an ajax callback to `LOGOUT_CALLBACK` to request deletion of the session
- Finally, the user is redirected to `LOGOUT_COMPLETE`


## DynamoDB (DDB) setup
Creates the table with a secondary index, and sets a time-to-live field
```
aws dynamodb create-table --table-name lambda_sessions \
    --attribute-definitions AttributeName=id,AttributeType=S AttributeName=sid,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --provisioned-throughput "ReadCapacityUnits=5,WriteCapacityUnits=5" \
    --global-secondary-indexes "IndexName=sid-index,KeySchema=[{AttributeName=sid,KeyType=HASH}],Projection={ProjectionType=KEYS_ONLY},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}"

aws dynamodb update-time-to-live --table-name lambda_sessions \
    --time-to-live-specification 'Enabled=true,AttributeName=ttl'
```

## IAM permissions

Managed Roles  
- AWSLambdaBasicExecutionRole  

Inline Policy  
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:DeleteItem",
                "dynamodb:GetItem",
                "dynamodb:Query"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/lambda_sessions/index/*",
                "arn:aws:dynamodb:*:*:table/lambda_sessions"
            ]
        }
    ]
}
```