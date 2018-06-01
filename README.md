# Cycloid toolkit

**Automated build for latest tag**

Docker image which contain tools and a scripts for cycloid.io deployment pipeline.

# Commands

## ansible-runner

This script use env vars configuration to run ansible playbook with ssh proxy on a bastion.

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
        BASTION_PRIVATE_KEY: ((bastion_ssh.ssh_key))
        ANSIBLE_VAULT_PASSWORD: ((ansible))
        AWS_ACCESS_KEY_ID: ((aws_admin.access_key))
        AWS_SECRET_ACCESS_KEY: ((aws_admin.secret_key))
        EXTRA_ARGS: "--limit tag_role_front"
        ANSIBLE_PLAYBOOK_PATH: ansible-playbook
        ANSIBLE_PLAYBOOK_NAME: ((customer)).yml
        EXTRA_VARS:
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
        AWS_ACCESS_KEY_ID: ((aws_admin.access_key))
        AWS_SECRET_ACCESS_KEY: ((aws_admin.secret_key))
        AWS_NAME_PATTERNS: >
                  [
                    "projcet1-front-prod",
                    "project1-batch-prod"
                  ]
```

**usage**

```
    - *aws-ami-cleaner
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
