# This is a makefile equivalent
# It's just convenient for executing tests.

export IMAGE_NAME := "cycloid/cycloid-toolkit:develop"
export PYTHON_VERSION := "3"
export ANSIBLE_VERSION := "8.*"

# run tests
default: tests

# build the docker image
build:
  docker build -t $IMAGE_NAME --build-arg=PYTHON_VERSION="$PYTHON_VERSION" --build-arg=ANSIBLE_VERSION="$ANSIBLE_VERSION" .

# build docker image and run tests
tests +test_case="": build
  python tests.py -v {{test_case}}

# use watchexec to execute `just <command>` when a python file changes
watch +command:
  watchexec -c -e ".py" -- just {{command}}
