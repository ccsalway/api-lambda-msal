#!/usr/bin/env bash
set -e  # halt on error

# Publishing serverless applications using the AWS SAM CLI
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-template-publishing-applications.html

source .env # export {AWS_PROFILE, STACK_NAME, AUTHORITY, CLIENT_ID, CLIENT_SECRET}

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
S3_BUCKET_NAME="aws-sam-sourcebucket-${AWS_ACCOUNT_ID}"
PACKAGE_NAME="./deploy/lambda_package.zip"

rm -rf {deploy,package}

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

echo "Configure the AAD application Redirect URI, Logout URL and Home page URL as per the README."
