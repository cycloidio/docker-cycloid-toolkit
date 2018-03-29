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

# Push new image tag

Tags are currently based on ansible version installed in the docker image.

> **If you update ansible version, push a new image tag**

```
sudo docker build . -t cycloid/cycloid-toolkit:v2.4
sudo docker push cycloid/cycloid-toolkit:v2.4
```
