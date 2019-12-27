# Pull base image
FROM alpine:3.6
LABEL Description="Cycloid toolkit" Vendor="Cycloid.io" Version="1.0"
MAINTAINER Cycloid.io

ARG PYTHON_VERSION=2
ARG ANSIBLE_VERSION=2.*

ADD requirements.txt /opt/

# Base packages
ADD files/ssh /root/.ssh
RUN chmod -R 600 /root/.ssh

# Contain ec2.py dynamic inventory from https://raw.githubusercontent.com/ansible/ansible/devel/contrib/inventory/ec2.py
COPY files/ansible /etc/ansible/
COPY scripts/* /usr/bin/

