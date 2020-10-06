# AWS Lambda Webapp template
Base source code for creating a lambda application that sits behind AAD authentication using OIDC. 

Acronyms: AAD - Azure Active Directory, DDB - DynamoDB

## Setup

Prerequisites
1. Ensure DDB table exists in the account you will deploy your application to - see below for DDB setup
2. Create an AAD application without a `Redirect URI` - you will add this later  

Setup - _see `deploy.sh` which can perform steps 3,4,5 for you_
1. Fork this repo for your new webapp
2. Create your views in the `views` directory - see file for example
    - each view needs a `view(request, response, session)` function to receive the request
    - static files are handled by the `lambda_function` and should be stored in `STATIC_PATH`
3. Create an IAM Role for the lambda to assume with the permission given below
4. Upload your app and assign the Lambda the IAM Role from the previous step, and the following
 environment variables from the AAD application:
    - `AUTHORITY` - https://login.microsoftonline.com/[Directory (tenant) ID]
    - `CLIENT_ID` - [Application (client) ID]
    - `CLIENT_SECRET` - (you will need to create one in the app under Certificates & secrets)
5. Create an AWS HTTP API Gateway (2.0) and route `ALL /{proxy+}` to the Lambda
6. Setup Route53 (DNS) if using it
7. Update the following fields in the AAD application:
    - `Branding / Home page URL` - set to `https://{domain_name}`
    - `Authentication / Redirect URI` - add `https://{domain_name}/auth/login/callback`
    - `Authentication / Logout URL` - set to `https://{domain_name}/auth/logout/callback`


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
- User is directed to the AAD logout process
- Once logged out, AAD makes an ajax callback to `LOGOUT_CALLBACK` where the `lambda_handler` deletes the session from DDB
- AAD then redirects the user to `LOGOUT_COMPLETE` where the session cookie is expired

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
