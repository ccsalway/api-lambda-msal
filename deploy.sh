#!/usr/bin/env bash

source .env  # file should contain:  export AWS_PROFILE=<profile_name>

rm -rf {deploy,package}

mkdir -p {deploy,package}

pip install -t ./package -r requirements.txt

(cd package || exit 1; zip -r9 "${OLDPWD}/deploy/lambda_function" .)
(cd src || exit 1; zip -rg "${OLDPWD}/deploy/lambda_function" .)

sam deploy --guided
