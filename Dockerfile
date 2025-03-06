# Pull base image
FROM alpine:3.18
LABEL Description="Cycloid toolkit" Vendor="Cycloid.io" Version="1.0"
MAINTAINER Cycloid.io

ARG PYTHON_VERSION=3
ARG ANSIBLE_VERSION=10.*

ADD requirements.txt /opt/
ADD requirements-vmware.txt /opt/

# Ansible Inventory galaxy collections
#   * Aws https://github.com/ansible-collections/amazon.aws#installing-this-collection
#   * GCP https://github.com/ansible-collections/google.cloud#installation
#   * Azure https://github.com/ansible-collections/azure#requirements
#   * Note: The if condition ensure we run this command only on Ansible version 2.9 and above. As collection is not available before.

# Base packages
RUN apk --upgrade add --no-cache \
        bash \
        sed \
        git \
        coreutils \
        sudo \
        curl \
        zip \
        jq \
        xmlsec \
        yaml \
        ipcalc \
        libxml2 \
        py${PYTHON_VERSION}-lxml \
        py${PYTHON_VERSION}-distutils-extra \
        pwgen \
        ncurses \
        mkpasswd \
        python${PYTHON_VERSION} \
        openssl \
        ca-certificates \
        openssh-client \
        rsync \
        patch \
        gettext \
        findutils \
        bc \
        tzdata \
        wget \
        py-pip \
        krb5 \
        google-authenticator \
    && \
      update-ca-certificates \
    && \
      apk --upgrade add --no-cache --virtual \
        build-dependencies \
        build-base \
        cargo \
        python${PYTHON_VERSION}-dev \
        libffi-dev \
        openssl-dev \
        linux-headers \
        libxml2-dev \
        libxslt-dev \
        musl-dev \
        krb5-dev \
    && \
      pip${PYTHON_VERSION} install pip --upgrade --break-system-packages && \
      pip${PYTHON_VERSION} install --upgrade --no-cache-dir -r /opt/requirements.txt --break-system-packages && \
      pip${PYTHON_VERSION} install --upgrade --no-cache-dir -r /opt/requirements-vmware.txt --break-system-packages && \
      pip${PYTHON_VERSION} install --upgrade --no-cache-dir ansible==${ANSIBLE_VERSION} --break-system-packages && \
      ansible-galaxy collection install google.cloud ansible.windows azure.azcollection amazon.aws --force && \
      pip${PYTHON_VERSION} install --upgrade --no-cache-dir -r /root/.ansible/collections/ansible_collections/azure/azcollection/requirements.txt --break-system-packages \
    && \
      ln -s $(which python${PYTHON_VERSION}) /bin/python \
    && \
      apk del \
        build-dependencies \
        build-base \
        cargo \
        python${PYTHON_VERSION}-dev \
        libffi-dev \
        openssl-dev \
        linux-headers \
        libxml2-dev \
        libxslt-dev \
        krb5-dev \
        musl-dev \
  && \
    rm -rf /var/cache/apk/*

ADD files/ssh /root/.ssh
RUN chmod -R 600 /root/.ssh

# Install aws ssm plugin
# https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-debian-and-ubuntu.html
# https://github.com/aws/session-manager-plugin/issues/12
RUN   apk add dpkg gcompat && \
      curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb" && \
      dpkg -x  session-manager-plugin.deb session-manager-plugin && \
      cp session-manager-plugin/usr/local/sessionmanagerplugin/bin/session-manager-plugin  /usr/bin/session-manager-plugin && \
      chmod +x /usr/bin/session-manager-plugin && \
      cp /usr/bin/session-manager-plugin /usr/local/bin/session-manager-plugin && \
      apk del dpkg

# TODO maybe deprecated could check to remove this api and ecr things
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

# Install Cycloid wrapper
RUN curl https://raw.githubusercontent.com/cycloidio/cycloid-cli/master/scripts/cy-wrapper.sh > /usr/bin/cy \
  && chmod +x /usr/bin/cy

# Install Changie
RUN wget -O changie.tar.gz https://github.com/miniscruff/changie/releases/download/v1.7.0/changie_1.7.0_linux_amd64.tar.gz \
  && tar xf changie.tar.gz changie \
  && rm changie.tar.gz \
  && chmod +x changie \
  && mv changie /usr/local/bin/changie

COPY files/ansible/etc /etc/ansible/
COPY files/ansible/plugins/callback/* /usr/share/ansible/plugins/callback/
COPY scripts/* /usr/bin/
