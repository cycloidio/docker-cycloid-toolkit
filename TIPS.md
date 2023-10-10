# Manually run ansible runner to test dynamic inventory at Cycloid

## Common requirements

```bash
mkdir -p /tmp/ansible-playbook
cat > /tmp/ansible-playbook/site.yml <<EOF
# Azure and Aws
#- hosts: tag_project_test:&tag_env_demo
# GCP
#- hosts: label_project_test:&label_env_demo
# Static
- hosts: all

  tasks:
    - name: Print the message
      ansible.builtin.debug:
        msg: "Hello"
EOF
```

Make sure to adapt host section depending the inventory you want to test

## Static inventory

```bash
cat > /tmp/ansible-playbook/inventory <<EOF
[all]
127.0.0.1
127.0.0.2
EOF

docker run -v /tmp/ansible-playbook:/tmp/ansible-playbook \
-e AWS_ACCESS_KEY_ID="" \
-e AWS_SECRET_ACCESS_KEY="" \
-e AWS_DEFAULT_REGION="" \
-e ANSIBLE_INVENTORY="inventory" \
-e ANSIBLE_PLAYBOOK_PATH="/tmp/ansible-playbook" \
-it $IMAGE_NAME bash -c "/usr/bin/ansible-runner-inventory"
# Or -it $IMAGE_NAME bash -c "/usr/bin/ansible-runner"
```

## AWS inventory

```bash
export AWS_ACCESS_KEY_ID=$(vault read -field=access_key secret/cycloid/aws)
export AWS_SECRET_ACCESS_KEY=$(vault read -field=secret_key secret/cycloid/aws)

docker run -v /tmp/ansible-playbook:/tmp/ansible-playbook \
-e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
-e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
-e AWS_DEFAULT_REGION="eu-west-1" \
-e ANSIBLE_PLAYBOOK_PATH="/tmp/ansible-playbook" \
-it $IMAGE_NAME bash -c "/usr/bin/ansible-runner-inventory"
# Or -it $IMAGE_NAME bash -c "/usr/bin/ansible-runner"
```

## Azure inventory

```bash
export AZURE_SUBSCRIPTION_ID=$(vault read -field=subscription_id secret/cycloid/azure/organization)
export AZURE_TENANT_ID=$(vault read -field=tenant_id secret/cycloid/azure/organization)
export AZURE_CLIENT_ID=$(vault read -field=client_id secret/cycloid/azure/app/ansible)
export AZURE_SECRET=$(vault read -field=client_secret secret/cycloid/azure/app/ansible)

docker run -v /tmp/ansible-playbook:/tmp/ansible-playbook \
-e AZURE_SUBSCRIPTION_ID="$AZURE_SUBSCRIPTION_ID" \
-e AZURE_TENANT_ID="$AZURE_TENANT_ID" \
-e AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
-e AZURE_SECRET="$AZURE_SECRET" \
-e ANSIBLE_PLAYBOOK_PATH="/tmp/ansible-playbook" \
-it $IMAGE_NAME bash -c "/usr/bin/ansible-runner-inventory"
# Or -it $IMAGE_NAME bash -c "/usr/bin/ansible-runner"
```


## GCP inventory

```bash
export GCP_SERVICE_ACCOUNT_CONTENTS=$(vault read -field=json-key secret/cycloid/gcp/cycloid-demo)

docker run -v /tmp/ansible-playbook:/tmp/ansible-playbook \
-e GCP_SERVICE_ACCOUNT_CONTENTS="$GCP_SERVICE_ACCOUNT_CONTENTS" \
-e ANSIBLE_PLAYBOOK_PATH="/tmp/ansible-playbook" \
-it $IMAGE_NAME bash -c "/usr/bin/ansible-runner-inventory"
# Or -it $IMAGE_NAME bash -c "/usr/bin/ansible-runner"
```

