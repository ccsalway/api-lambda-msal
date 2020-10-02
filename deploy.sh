#!/usr/bin/env bash
set -e  # halt on error

# To deploy using this shell script, you need to have installed AWS SAM CLI (see link below)
# as well as created a .env file with the following contents:
#   export AWS_PROFILE=<aws profile name for the aws cli>
#   export STACK_NAME=<a name for the aws stack>
#   export AUTHORITY=<authority URL of the AAD application>
#   export CLIENT_ID=<AAD application (client) ID>
#   export CLIENT_SECRET=<AAD application secret>

# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-template-publishing-applications.html

source .env

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
S3_BUCKET_NAME="aws-sam-sourcebucket-${AWS_ACCOUNT_ID}"
PACKAGE_NAME="./deploy/lambda_package.zip"

rm -rf {deploy,package}  # clean start

mkdir -p {deploy,package}

pip install -t ./package -r requirements.txt

(cd package || exit 1; zip -r9 ".${PACKAGE_NAME}" .)
(cd src || exit 1; zip -rg ".${PACKAGE_NAME}" .)

if [[ -z $(aws s3api list-buckets --query "Buckets[?Name=='${S3_BUCKET_NAME}']" --output text) ]]; then
  aws s3 mb s3://${S3_BUCKET_NAME}
fi

sam deploy \
  --template-file template.yaml \
  --parameter-overrides "Authority=\"${AUTHORITY}\" ClientID=\"${CLIENT_ID}\" ClientSecret=\"${CLIENT_SECRET}\"" \
  --stack-name "aws-sam-${STACK_NAME}" \
  --capabilities "CAPABILITY_IAM" \
  --s3-bucket "${S3_BUCKET_NAME}" \
  --s3-prefix "${STACK_NAME}" \
  --confirm-changeset

rm -rf {deploy,package}  # clean-up

echo "Configure the AAD application Redirect URI, Logout URL and Home page URL with the HttpApiUrl."
