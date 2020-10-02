#!/usr/bin/env bash
set -e

source .env  # export {AWS_PROFILE, STACK_NAME, AUTHORITY, CLIENT_ID, CLIENT_SECRET}

rm -rf {deploy,package}

mkdir -p {deploy,package}

pip install -t ./package -r requirements.txt

(cd package || exit 1; zip -r9 "${OLDPWD}/deploy/lambda_function" .)
(cd src || exit 1; zip -rg "${OLDPWD}/deploy/lambda_function" .)

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
S3_BUCKET_NAME="aws-sam-default-sourcebucket-${AWS_ACCOUNT_ID}"

if [[ -z $(aws s3api list-buckets --query "Buckets[?Name=='${S3_BUCKET_NAME}']" --output text) ]]; then
  aws s3 mb s3://${S3_BUCKET_NAME}
fi

sam deploy --stack-name "aws-sam-default-${STACK_NAME}" \
--capabilities CAPABILITY_IAM \
--parameter-overrides "Authority=\"${AUTHORITY}\" ClientID=\"${CLIENT_ID}\" ClientSecret=\"${CLIENT_SECRET}\"" \
--s3-bucket ${S3_BUCKET_NAME} \
--s3-prefix "${STACK_NAME}" \
--confirm-changeset

# clean up
rm -rf {deploy,package}
