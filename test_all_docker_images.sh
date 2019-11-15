#!/bin/bash
set -e

# Build locally all images
# bash hooks/build

# If you want to run it with a clear python version
# virtualenv -p python3 --clear .env
# source .env/bin/activate
# pip install unittest2 docker

export DOCKER_REPO="${DOCKER_REPO:-cycloid/cycloid-toolkit}"
export DOCKER_TAG="${DOCKER_TAG:-develop}"


# Test against all uploaded docker images on dockerhub.
#for tag in $(curl https://hub.docker.com/v2/repositories/cycloid/cycloid-toolkit/tags/ | jq -r '.results[].name'); do

IFS=$'\n'
for line in $(cat .versions); do
    python_version=$(echo $line | awk '{print $1}')
    ansible_version=$(echo $line | awk '{print $2}')
    tag=$(echo $line | awk '{print $3}')
    if [[ "$tag" == "default_tag" ]]; then
        tag=$DOCKER_TAG
    fi

    export IMAGE_NAME="${DOCKER_REPO}:${tag}"
    echo "######## IMAGE_NAME=${IMAGE_NAME} PYTHON_VERSION=${python_version} ANSIBLE_VERSION=${ansible_version%.*}"
    python tests.py -vvvv
done
unset IFS
