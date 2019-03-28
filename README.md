# Cycloid toolkit

**Automated build for latest tag**

Docker image which contain tools and a scripts for cycloid.io deployment pipeline.

# Commands

## ansible-runner

This script use env vars configuration to run ansible playbook with ssh proxy on a bastion.

./ansible-runner
  * `AWS_ACCESS_KEY_ID` : Used by Amazon EC2 dynamic inventory
  * `AWS_SECRET_ACCESS_KEY`: Used by Amazon EC2 dynamic inventory
  * `SSH_PRIVATE_KEY` : SSH key to use to connect on servers
  * `(BASTION_URL)` : SSH url of the bastion server. Exemple : `admin@myserver.com`
  * `(TAGS)`: Only run plays and tasks tagged with these values
  * `(SKIP_TAGS)` : only run plays and tasks whose tags do not match these values
  * `(EXTRA_ANSIBLE_ARGS)` Additional ansible-playbook arguments
  * `(EXTRA_ANSIBLE_VARS)` json dict format. Ansible extra-vars, set additional variables
  * `(ANSIBLE_REMOTE_USER)` default : `admin` Ansible remote user
  * `(ANSIBLE_GALAXY_EXTRA_ARGS)` Additional ansible-galaxy arguments
  * `(ANSIBLE_VAULT_PASSWORD)` : Vault password if you use [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html) files
  * `(ANSIBLE_FORCE_GALAXY)` default `false`. Force to run Ansible galaxy to updated eventual cached ansible roles
  * `(ANSIBLE_PLAYBOOK_NAME)` default : `site.yml` Name of the ansible playbook to run
  * `(ANSIBLE_PLAYBOOK_PATH)` default : `ansible-playbook` Path of the ansible playbook to run
ec2.py vars :
  * (EC2_VPC_DESTINATION_VARIABLE) default private_ip_address see https://github.com/ansible/ansible/blob/devel/contrib/inventory/ec2.ini

Example of pipeline configuration :

**YAML anchors**

```
shared:
  - &run-ansible-from-bastion
    config:
      platform: linux
      image_resource:
        type: docker-image
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

```
    - task: run-ansible
      <<: *run-ansible-from-bastion
      params:
        BASTION_URL: ((bastion_url))
        SSH_PRIVATE_KEY: ((bastion_ssh.ssh_key))
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

## aws-ami-cleaner

Provide a way to clean old Amazon AMI. Usually usefull whan you often build new AMI for your ASG.

Example of pipeline configuration :

**YAML anchors**

```
shared:
  - &aws-ami-cleaner
    task: aws-ami-cleaner
    config:
      platform: linux
      image_resource:
        type: docker-image
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

```
shared:
  - &aws-ecr-cleaner
    task: aws-ecr-cleaner
    config:
      platform: linux
      image_resource:
        type: docker-image
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

```
shared:
  - &vault-approle-login
    task: vault-approle-login
    config:
      platform: linux
      image_resource:
        type: docker-image
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

## merge-stack-and-config

This script use env vars configuration to merge stack and config for Cycloid.io.

**YAML anchors**

```
shared:
  - &merge-stack-and-config
    platform: linux
    image_resource:
      type: docker-image
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

```
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


# Push new image tag

Tags are currently based on ansible version installed in the docker image.

> **If you update ansible version, push a new image tag**

```
sudo docker build . -t cycloid/cycloid-toolkit:v2.4
sudo docker push cycloid/cycloid-toolkit:v2.4
```
