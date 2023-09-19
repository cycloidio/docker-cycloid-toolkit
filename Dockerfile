# Pull base image
FROM alpine:3.18
LABEL Description="Cycloid toolkit" Vendor="Cycloid.io" Version="1.0"
MAINTAINER Cycloid.io

ARG PYTHON_VERSION=3
ARG ANSIBLE_VERSION=8.*

ADD requirements.txt /opt/
ADD requirements-vmware.txt /opt/

# Base packages
RUN ln -s /lib /lib64 \
    && \
        apk --upgrade add --no-cache \
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
            libc6-compat \
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
        pip${PYTHON_VERSION} install pip --upgrade && \
        pip${PYTHON_VERSION} install --upgrade --no-cache-dir -r /opt/requirements.txt && \
        pip${PYTHON_VERSION} install --upgrade --no-cache-dir -r /opt/requirements-vmware.txt && \
        pip${PYTHON_VERSION} install --upgrade --no-cache-dir ansible==${ANSIBLE_VERSION} \
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

# Contain ec2.py dynamic inventory from https://github.com/ansible-collections/community.aws/tree/main/scripts/inventory or https://github.com/ansible/ansible/blob/stable-2.9/contrib/inventory/ec2.py
COPY files/ansible /etc/ansible/
COPY scripts/* /usr/bin/

# Install Ansible galaxy collections
# Note: The if condition ensure we run this command only on Ansible version 2.9 and above. As collection is not available before.
RUN if [[ "$( echo -e "${ANSIBLE_VERSION}\n2.8\n" | sed -r 's/^([0-9]+\.[0-9]+).*$/\1/g' | sort -V | tail -n1)" != "2.8" ]]; then ansible-galaxy collection install google.cloud ansible.windows azure.azcollection; fi
