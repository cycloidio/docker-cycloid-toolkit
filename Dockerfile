# Pull base image
FROM alpine:3.6
LABEL Description="Cycloid toolkit" Vendor="Cycloid.io" Version="1.0"
MAINTAINER Cycloid.io

ARG PYTHON_VERSION=2
ARG ANSIBLE_VERSION=2.*

ADD requirements.txt /opt/

# Base packages
RUN ln -s /lib /lib64 \
    && \
        apk --upgrade add --no-cache \
            bash \
            sed \
            git \
            sudo \
            curl \
            zip \
            jq \
            xmlsec \
            yaml \
            ipcalc \
            libc6-compat \
            libxml2 \
            py-lxml \
            pwgen \
            python${PYTHON_VERSION} \
            openssl \
            ca-certificates \
            openssh-client \
            rsync \
            patch \
            gettext \
            findutils \
    && \
        if [ ${PYTHON_VERSION} -eq 2 ]; then apk add --no-cache py-pip; fi \
    && \
        apk --upgrade add --no-cache --virtual \
            build-dependencies \
            build-base \
            python${PYTHON_VERSION}-dev \
            libffi-dev \
            openssl-dev \
            linux-headers \
            libxml2-dev \
    && \
        pip${PYTHON_VERSION} install pip --upgrade && \
        pip${PYTHON_VERSION} install --upgrade --no-cache-dir -r /opt/requirements.txt && \
        pip${PYTHON_VERSION} install --upgrade --no-cache-dir ansible==${ANSIBLE_VERSION} \
    && \
        ln -s $(which python${PYTHON_VERSION}) /bin/python \
    && \
        apk del \
            build-dependencies \
            build-base \
            python${PYTHON_VERSION}-dev \
            libffi-dev \
            openssl-dev \
            linux-headers \
            libxml2-dev \
    && \
        rm -rf /var/cache/apk/*

ADD files/ssh /root/.ssh
RUN chmod -R 600 /root/.ssh

# Install ec2 ami cleaner
RUN git clone https://github.com/cycloidio/aws-amicleaner \
    && cd aws-amicleaner \
    && pip${PYTHON_VERSION} install --no-cache-dir -q -e . \
    && pip${PYTHON_VERSION} install --no-cache-dir -q future \
    && rm -rf .git

# Install ecr image cleaner
RUN curl https://raw.githubusercontent.com/cycloidio/ecr-cleanup-lambda/master/main.py > /usr/bin/aws-ecr-cleaner \
    && chmod +x /usr/bin/aws-ecr-cleaner

#TMP fix for https://github.com/boto/boto/issues/3783
# eu-west-3 region is not supported by boto, we need to override the aws endpoints with the existing new regions
RUN curl https://raw.githubusercontent.com/aws/aws-sdk-net/master/sdk/src/Core/endpoints.json > /etc/endpoints_new.json \
    && pip${PYTHON_VERSION} install --no-cache-dir --upgrade boto \
    && cp /etc/endpoints_new.json $(python${PYTHON_VERSION} -c "import boto; print('%s/endpoints.json' % boto.__path__[0])")

# Contain ec2.py dynamic inventory from https://raw.githubusercontent.com/ansible/ansible/devel/contrib/inventory/ec2.py
COPY files/ansible/ /etc/ansible/
COPY scripts/* /usr/bin/

# Patching ansible https://github.com/ansible/ansible/pull/47867
#  diff -Naur aws_s3.py.orig aws_s3.py > patch
#  editdiff patch
RUN patch -i /etc/ansible/patch_s3_object_version $(python${PYTHON_VERSION} -c "import ansible; print('%s/modules/cloud/amazon/aws_s3.py' % ansible.__path__[0])")
