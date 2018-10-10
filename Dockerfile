# Pull base image
FROM alpine:3.6
LABEL Description="Cycloid toolkit" Vendor="Cycloid.io" Version="1.0"
MAINTAINER Cycloid.io

# Base packages
# Build dependencies
RUN ln -s /lib /lib64 \
    && \
        apk --upgrade add --no-cache \
            bash \
            git \
            sudo \
            curl \
            zip \
            jq \
            xmlsec \
            yaml \
            libc6-compat \
            python \
            libxml2 \
            py-lxml \
            py-pip \
            openssl \
            ca-certificates \
            openssh-client \
            rsync \
    && \
        apk --upgrade add --no-cache --virtual \
            build-dependencies \
            build-base \
            python-dev \
            libffi-dev \
            openssl-dev \
            linux-headers \
            libxml2-dev

# Ansible installation
ADD requirements.txt /opt/
RUN pip install pip --upgrade
RUN pip install --upgrade --no-cache-dir -r /opt/requirements.txt

RUN apk del \
        build-dependencies \
        build-base \
        python-dev \
        libffi-dev \
        openssl-dev \
        linux-headers \
        libxml2-dev \
    && \
        rm -rf /var/cache/apk/*

ADD files/ssh /root/.ssh
RUN chmod -R 600 /root/.ssh

# Install ec2 ami cleaner
RUN git clone https://github.com/bonclay7/aws-amicleaner \
    && cd aws-amicleaner \
    && pip install -q -e . \
    && pip install -q future

# Install ecr image cleaner
RUN wget https://raw.githubusercontent.com/cycloidio/ecr-cleanup-lambda/master/main.py -O /usr/bin/aws-ecr-cleaner \
    && chmod +x /usr/bin/aws-ecr-cleaner

#TMP fix for https://github.com/boto/boto/issues/3783
# eu-west-3 region is not supported by boto, we need to override the aws endpoints with the existing new regions
RUN curl https://raw.githubusercontent.com/aws/aws-sdk-net/master/sdk/src/Core/endpoints.json > /etc/endpoints_new.json \
    && pip install --upgrade boto \
    && cp /etc/endpoints_new.json /usr/lib/python2.7/site-packages/boto/endpoints.json

# Contain ec2.py dynamic inventory from https://raw.githubusercontent.com/ansible/ansible/devel/contrib/inventory/ec2.py
COPY files/ansible/ /etc/ansible/
COPY scripts/* /usr/bin/
