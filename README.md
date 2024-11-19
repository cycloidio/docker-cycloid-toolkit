# Cycloid toolkit

**Automated build for latest tag**

Docker image which contain tools and a scripts for cycloid.io deployment pipeline.

**azure-latest**

Due to https://github.com/Azure/azure-cli/issues/22955, the azure cli is not included in the basic toolkit image.
We currently provide a build of the toolkit with azure cli under the `azure-latest` tag.

Build note for this image:

```bash
docker build -t cycloid/cycloid-toolkit:azure-latest -f Dockerfile.azure .
docker push cycloid/cycloid-toolkit:azure-latest
```

**gcp-latest**

Due to the same reason as Azure image size, we currently provide a build of the toolkit with gcp cli under the `gcp-latest` tag.

Build note for this image:

```bash
docker build -t cycloid/cycloid-toolkit:gcp-latest -f Dockerfile.gcp .
docker push cycloid/cycloid-toolkit:gcp-latest
```

# Commands

## ansible-runner

This script use env vars configuration to run ansible playbook with ssh proxy on a bastion.

./scripts/ansible-runner
  * `(SSH_PRIVATE_KEY)`: SSH key to use to connect on servers
  * `(SSH_PRIVATE_KEYS)`: SSH key array to use to connect on servers. Example: ["PRIVATE_KEY","PRIVATE_KEY"]
  * `(BASTION_URL)`: [DEPRECATED] SSH URL of the bastion server. Example: `admin@myserver.com`
  * `(SSH_JUMP_URL)`: SSH ProxyJump URL used with `ssh ProxyJump`. Example: `user1@Bastion1,user2@Bastion2`
  * `(TAGS)`: Only run plays and tasks tagged with these values
  * `(SKIP_TAGS)`: Only run plays and tasks whose tags do not match these values
  * `(EXTRA_ANSIBLE_ARGS)`: Additional ansible-playbook arguments
  * `(EXTRA_ANSIBLE_VARS)`: Ansible extra-vars, set additional variables, json dict format.
  * `(ANSIBLE_REMOTE_USER)`: Ansible remote user. Default: `admin`.
  * `(ANSIBLE_LIMIT_HOSTS)`: Select a subset of the inventory
  * `(ANSIBLE_GALAXY_EXTRA_ARGS)`: Additional ansible-galaxy arguments
  * `(ANSIBLE_VAULT_PASSWORD)`: Vault password if you use [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html) files
  * `(ANSIBLE_FORCE_GALAXY)`: Force to run Ansible galaxy to updated eventual cached ansible roles. Default: `false`.
  * `(ANSIBLE_PLAYBOOK_NAME)`: Name of the ansible playbook to run. Default: `site.yml`.
  * `(ANSIBLE_PLAYBOOK_PATH)`: Path of the ansible playbook to run. Default: `ansible-playbook`.
  * `(ANSIBLE_FAIL_WHEN_NO_HOST)`: Fail when no host is found. Default: `false`.
  * `(DEBUG)`: Run in debug mode

ansible-common:
  * `(ANSIBLE_STDOUT_CALLBACK)`: Callback plugin used for ansible output. Example: `default` can be used to see debug messages. Default: `actionable`.

AWS ec2 inventory:
  * `(AWS_INVENTORY)`: If the Amazon EC2 dynamic inventory need to be used or no, can be eiter `true`, `false` or `auto`. `auto` checks if `AWS_ACCESS_KEY_ID` is set or not. Default: `auto`.
  * Cloud access used by Amazon EC2 dynamic inventory
     - `(CY_AWS_CRED)`: Use Cycloid AWS credential
    or
     - `(AWS_ACCESS_KEY_ID)`: Used by Amazon EC2 dynamic inventory
     - `(AWS_SECRET_ACCESS_KEY)`: Used by Amazon EC2 dynamic inventory
  * `(AWS_EC2_COMPOSE_ANSIBLE_HOST)`: Can be either `public_ip_address` for public ip address or `private_ip_address`, see [ansible_doc](https://docs.ansible.com/ansible/latest/collections/amazon/aw    s/aws_ec2_inventory.html) or run ansible-runner-inventory to see available choices. Default: `private_ip_address`

Azure azure_rm inventory:
  * `(AZURE_INVENTORY)`: If the Azure dynamic inventory need to be used or no, can be eiter `true`, `false` or `auto`. `auto` checks if `AZURE_SUBSCRIPTION_ID` is set or not. Default: `auto`.
  * Cloud access used by Azurerm dynamic inventory
     - `(CY_AZURE_CRED)`: Use Cycloid Azure credential
    or
     - `(AZURE_SUBSCRIPTION_ID)`: Used by Azure dynamic inventory
     - `(AZURE_TENANT_ID)`: Used by Azure dynamic inventory
     - `(AZURE_CLIENT_ID)`: Used by Azure dynamic inventory
     - `(AZURE_SECRET)`: Used by Azure dynamic inventory
  * `(AZURE_USE_PRIVATE_IP)`: Can be either `True` or `False`, see [azure_rm.py](https://raw.githubusercontent.com/ansible/ansible/devel/contrib/inventory/azure_rm.py). Default: `True`.
  * `(ANSIBLE_PLUGIN_AZURE_PLAIN_HOST_NAMES)`: By default this plugin will use globally unique host names. This option allows you to override that, and use the name that matches the old inventory script naming.. Default: `False`.
  note: Ansible `azure_rm` plugin is used for ansible `>= 2.8` else `azure_rm.py` script will be used

GCP gcp_compute inventory:
  * `(GCP_INVENTORY)`: If the GCP dynamic inventory needs to be used or not, can be either `true`, `false` or `auto`. `auto` checks if `GCP_SERVICE_ACCOUNT_CONTENTS` is set or not. Default: `auto`.
  * Cloud access used by Google compute dynamic inventory
     - `(CY_GCP_CRED)`: Use Cycloid GCP credential
    or
     - `(GCP_SERVICE_ACCOUNT_CONTENTS)`: Used by GCP dynamic inventory. The GCP Service Account in JSON format.
  * `(GCP_USE_PRIVATE_IP)`: Can be either `True` or `False`. Default: `True`.

vmware_vm_inventory vars:
  * `(VMWARE_VM_INVENTORY)`: If the VMware Guest inventory needs to be used or not, can be either `true`, `false` or `auto`. `auto` checks if `VMWARE_SERVER` is set or not. Default: `auto`.
  * `(VMWARE_SERVER)`: Used by VMware Guest inventory. Name or IP address of vCenter server.
  * `(VMWARE_PORT)`: Used by VMware Guest inventory. Service port of vCenter server. Default: 443
  * `(VMWARE_USERNAME)`: Used by VMware Guest inventory. Name of vSphere user.
  * `(VMWARE_PASSWORD)`: Used by VMware Guest inventory. Password of vSphere user.

Example of pipeline configuration :

**YAML anchors**

```YAML
shared:
  - &run-ansible-from-bastion
    config:
      platform: linux
      image_resource:
        type: registry-image
        source:
          repository: cycloid/cycloid-toolkit
          tag: latest
      run:
        path: /usr/bin/ansible-runner
      caches:
        - path: ansible-playbook/roles
      inputs:
      - name: ansible-playbook
        path: ansible-playbook
```

**usage**

```YAML
    - task: run-ansible
      <<: *run-ansible-from-bastion
      params:
        SSH_JUMP_URL: ((bastion_url))
        SSH_PRIVATE_KEY: ((bastion_ssh.ssh_key))
        SSH_PRIVATE_KEYS:
          - ((user1_ssh.ssh_key))
          - ((user2_ssh.ssh_key))
        ANSIBLE_VAULT_PASSWORD: ((ansible))
        AWS_ACCESS_KEY_ID: ((aws_access_key))
        AWS_SECRET_ACCESS_KEY: ((aws_secret_key))
        EXTRA_ANSIBLE_ARGS: "--limit tag_role_front"
        AWS_DEFAULT_REGION: eu-west-1
        ANSIBLE_PLAYBOOK_PATH: ansible-playbook
        ANSIBLE_PLAYBOOK_NAME: ((customer)).yml
        EXTRA_ANSIBLE_VARS:
          customer: ((customer))
          project: ((project))
          env: ((env))
        TAGS:
          - deploy
```

## ansible-runner-inventory

This script use env vars configuration to run ansible-inventory command. Purpose is to help troubleshooting Ansible inventory issues
keeping all features and automatic inventory load from ansible-common.sh

./scripts/ansible-runner-inventory
  * `(ANSIBLE_PLAYBOOK_PATH)`: Path of the ansible playbook to run. Default: `ansible-playbook`.

Example of pipeline configuration :

**YAML anchors**

```YAML
shared:
  - &run-ansible-inventory
    config:
      platform: linux
      image_resource:
        type: registry-image
        source:
          repository: cycloid/cycloid-toolkit
          tag: latest
      run:
        path: /usr/bin/ansible-runner-inventory
      inputs:
      - name: ansible-playbook
        path: ansible-playbook
```

**usage**

```YAML
    - task: run-ansible
      <<: *run-ansible-inventory
      params:
        AWS_ACCESS_KEY_ID: ((aws_access_key))
        AWS_SECRET_ACCESS_KEY: ((aws_secret_key))
        ANSIBLE_PLAYBOOK_PATH: ansible-playbook
```

## aws-ami-cleaner

Provide a way to clean old Amazon AMI. Usually usefull whan you often build new AMI for your ASG.

Example of pipeline configuration :

**YAML anchors**

```YAML
shared:
  - &aws-ami-cleaner
    task: aws-ami-cleaner
    config:
      platform: linux
      image_resource:
        type: registry-image
        source:
          repository: cycloid/cycloid-toolkit
          tag: latest
      run:
        path: /usr/bin/aws-ami-cleaner
      params:
        AWS_ACCESS_KEY_ID: ((aws_access_key))
        AWS_SECRET_ACCESS_KEY: ((aws_secret_key))
        AWS_NAME_PATTERNS: >
                  [
                    "projcet1_front_prod",
                    "project1_batch_prod"
                  ]
```

**usage**

```
    - *aws-ami-cleaner
```


## aws-ecr-cleaner

Provide a way to clean old docker images from ECR. Usually usefull whan you often build new image for your ecs.

Example of pipeline configuration :

**YAML anchors**

```YAML
shared:
  - &aws-ecr-cleaner
    task: aws-ecr-cleaner
    config:
      platform: linux
      image_resource:
        type: registry-image
        source:
          repository: cycloid/cycloid-toolkit
          tag: latest
      run:
        path: /usr/bin/aws-ecr-cleaner
      params:
        AWS_ACCESS_KEY_ID: ((aws_access_key))
        AWS_SECRET_ACCESS_KEY: ((aws_secret_key))
        REGION: ((aws_default_region))
        DRYRUN: False
        IMAGES_TO_KEEP: 2
        REPOSITORIES_FILTER: 'foo bar'
        # For a global clean with exclude:
        IGNORE_TAGS_REGEX: 'dev|staging|prod|latest-'
        # For a clean on specific tag/env
        FILTER_TAGS_REGEX: '^dev-'
```

**usage**

```
    - *aws-ecr-cleaner
```


## vault-approle-login

This script use env vars configuration to get a vault token using approle auth.
The token is inserted in a tf variable file.

Example of pipeline configuration :

**YAML anchors**

```YAML
shared:
  - &vault-approle-login
    task: vault-approle-login
    config:
      platform: linux
      image_resource:
        type: registry-image
        source:
          repository: cycloid/cycloid-toolkit
          tag: latest
      run:
        path: /usr/bin/vault-approle-login
      outputs:
      - name: vault-token
        path: vault-token
    params:
      VAULT_ROLEID: ((vault.role_id))
      VAULT_SECRETID: ((vault.secret_id))
```

**usage**

```
  - *vault-approle-login
```

## extract-terraform-outputs

This script is mostly expected to be used by the `merge-stack-and-config` script.
Its purpose is to export all terraform outputs as both a YAML and shell script files in addition to loading them as environment variables in the current shell execution scope.

./scripts/extract-terraform-outputs
  * `(TERRAFORM_METADATA_FILE)` Defaults to `terraform/metadata` and fallback to TERRAFORM_DEFAULT_METADATA_FILE.'
  * `(TERRAFORM_DEFAULT_METADATA_FILE)` Defaults to `tfstate/metadata`.'
  * `(OUTPUT_ANSIBLE_VAR_FILE)` Ansible variables file. Defaults to `output-var/all`. You might want to use `ansible-playbook/group_vars/all`.'
  * `(OUTPUT_ENV_VAR_FILE)` Shell environment variables file. Defaults to `output-var/env`. Special chars in variable name are replaced by "_"'
  * `(OUTPUT_VAR_PATH)` base path used for all *_VAR_FILE. Defaults to `output-var`.'


## merge-stack-and-config

This script use env vars configuration to merge stack and config for Cycloid.io.

**YAML anchors**

```YAML
shared:
  - &merge-stack-and-config
    platform: linux
    image_resource:
      type: registry-image
      source:
        repository: cycloid/cycloid-toolkit
        tag: latest
    run:
      path: /usr/bin/merge-stack-and-config
    outputs:
    - name: merged-stack
      path: "merged-stack"

```

**usage**

```YAML
    - task: merge-stack-and-config
      config:
        <<: *merge-stack-and-config
        inputs:
        - name: ((project))-config-ansible
          path: "config"
        - name: ((project))-stack-ansible
          path: "stack"
        # Provide terraform outputs to add them as ansible vars
        - name: ((project))-terraform-apply
          path: "terraform"
      params:
        CONFIG_PATH: ((project))/ansible
        STACK_PATH: stack-((project))/ansible
```


# Build and test a local image

```bash
export IMAGE_NAME="cycloid/cycloid-toolkit:develop"
export PYTHON_VERSION=3
export ANSIBLE_VERSION=10.*
docker build -t $IMAGE_NAME --build-arg=PYTHON_VERSION="$PYTHON_VERSION" --build-arg=ANSIBLE_VERSION="$ANSIBLE_VERSION" .

virtualenv -p python3 --clear .env
source .env/bin/activate
pip install unittest2 docker
python tests.py -v
```


# Push new image tag

Tags are currently based on ansible version installed in the docker image.

> **If you update ansible version, push a new image tag**

```
sudo docker build . -t cycloid/cycloid-toolkit:v2.9
sudo docker push cycloid/cycloid-toolkit:v2.9
```
