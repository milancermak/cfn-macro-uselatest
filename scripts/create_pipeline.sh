#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

#
# This script first creates an artifacts bucket for the CD pipeline
# in each available AWS region to make the macro available everywhere.
# Then it creates the CodePipeline declared in the
# infrastructure/pipeline.yml template.
#

readonly SERVICE_NAME="cfn-macro-uselatest"
readonly PIPELINE_STACK_NAME="${SERVICE_NAME}-pipeline"
readonly ARTIFACTS_BUCKET_BASE_NAME="${PIPELINE_STACK_NAME}-artifacts"
readonly BUCKET_ENCRYPTION_CONFIG=$(cat <<-EOF
{"Rules": [
    {
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms"
      }
    }
  ]
}
EOF
)

readonly DIR="$(cd "$(dirname "$0")" ; pwd -P)"
readonly INFRADIR="${DIR}/../infrastructure"

readonly REGIONS="\
  ap-northeast-1 \
  ap-northeast-2 \
  ap-south-1 \
  ap-southeast-1 \
  ap-southeast-2 \
  ca-central-1 \
  eu-central-1 \
  eu-west-1 \
  eu-west-2 \
  eu-west-3 \
  sa-east-1 \
  us-east-1 \
  us-east-2 \
  us-west-1 \
  us-west-2 \
"

for region in $REGIONS; do
    BUCKET_NAME="${ARTIFACTS_BUCKET_BASE_NAME}-${region}"
    aws s3 mb "s3://${BUCKET_NAME}" --region ${region} && \
    aws s3api put-bucket-encryption --region ${region} \
        --bucket ${BUCKET_NAME} \
        --server-side-encryption-configuration "${BUCKET_ENCRYPTION_CONFIG}" &
done

echo 'Waiting for regional artifact buckets to be created'
for job in $(jobs -p); do
    wait $job
done

echo 'Creating pipeline stack'
aws cloudformation create-stack \
    --stack-name ${PIPELINE_STACK_NAME} \
    --template-body file://${INFRADIR}/pipeline.yml \
    --parameters ParameterKey=Service,ParameterValue="${SERVICE_NAME}" \
    --tags Key=Service,Value=${SERVICE_NAME} \
    --on-failure DELETE \
    --capabilities CAPABILITY_IAM

aws cloudformation wait stack-create-complete --stack-name ${PIPELINE_STACK_NAME}
