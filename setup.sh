#!/usr/bin/env bash

# https://docs.aws.amazon.com/lambda/latest/dg/python-package.html

source .env

rm -rf {deploy,package}

mkdir -p {deploy,package}

pip install -t ./package -r requirements.txt

(cd package || exit 1; zip -r9 "${OLDPWD}/deploy/lambda_function" .)
zip -rg deploy/lambda_function templates config.py lambda* session*

aws lambda update-function-code --function-name msal-demo --zip-file fileb://deploy/lambda_function.zip

#aws lambda create-function \
#    --function-name msal-demo \
#    --runtime python3.8 \
#    --zip-file fileb://deploy/lambda_function.zip \
#    --handler lambda_function.lambda_handler \
#    --role arn:aws:iam::865789842342:role/AWSLambdaRoleMSALdemo \
#    --timeout 60 \
#    --publish
