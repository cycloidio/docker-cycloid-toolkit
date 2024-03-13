export IMAGE_NAME := "cycloid/cycloid-toolkit:develop"
export PYTHON_VERSION := "3"
export ANSIBLE_VERSION := "8.*"

default: tests

build:
  docker build -t $IMAGE_NAME --build-arg=PYTHON_VERSION="$PYTHON_VERSION" --build-arg=ANSIBLE_VERSION="$ANSIBLE_VERSION" .

tests: build
  python tests.py -v

watch +command:
  watchexec -c -e ".py" -- just {{command}}
