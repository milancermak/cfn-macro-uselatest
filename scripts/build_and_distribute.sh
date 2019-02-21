#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

#
# This script

#
# This script first creates an artifacts bucket for the CD pipeline
# in each available AWS region to make the macro available everywhere.
# Then it creates the CodePipeline declared in the
# infrastructure/pipeline.yml template.
#

readonly SERVICE_NAME="cfn-macro-uselatest"
readonly PIPELINE_STACK_NAME="${SERVICE_NAME}-pipeline"
readonly ARTIFACTS_BUCKET_BASE_NAME="${PIPELINE_STACK_NAME}-artifacts"

readonly DIR="$(cd "$(dirname "$0")" ; pwd -P)"
readonly BUILD_DIR="${DIR}/../build"

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

sam build \
    --build-dir ${BUILD_DIR} \
    --template "${DIR}/../infrastructure/uselatest.yml"

for region in $REGIONS; do
    BUCKET_NAME="${ARTIFACTS_BUCKET_BASE_NAME}-${region}"
    REGIONAL_STACK_TEMPLATE="packaged-${region}.yml"
    sam package \
        --template-file "${BUILD_DIR}/template.yaml" \
        --s3-bucket ${BUCKET_NAME} \
        --output-template-file "${BUILD_DIR}/${REGIONAL_STACK_TEMPLATE}" > /dev/null &
done

echo 'Distribution of artifacts to regions in progress'
for job in $(jobs -p); do
    wait $job
done
