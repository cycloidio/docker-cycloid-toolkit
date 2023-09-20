#!/bin/bash

set -e

if [ -n "$DEBUG" ]; then
  set -x
fi

# Keep compatibility with old namings
export SSH_PRIVATE_KEY="${SSH_PRIVATE_KEY:-$BASTION_PRIVATE_KEY}"
export EXTRA_ANSIBLE_VARS="${EXTRA_ANSIBLE_VARS:-$EXTRA_VARS}"
export EXTRA_ANSIBLE_ARGS="${EXTRA_ANSIBLE_ARGS:-$EXTRA_ARGS}"
export ANSIBLE_EXTRA_ARGS="${ANSIBLE_EXTRA_ARGS:-$EXTRA_ANSIBLE_ARGS}"
export ANSIBLE_EXTRA_VARS="${ANSIBLE_EXTRA_VARS:-$EXTRA_ANSIBLE_VARS}"
export AWS_EC2_COMPOSE_ANSIBLE_HOST="${AWS_EC2_COMPOSE_ANSIBLE_HOST:-$EC2_VPC_DESTINATION_VARIABLE}"

export CYCLOID_WORKDIR=$PWD
export ANSIBLE_VERSION="$(ansible --version | head -n1 | sed -r 's/[^0-9]+([0-9\.]+)[^0-9]+/\1/')"
export ANSIBLE_REMOTE_USER="${ANSIBLE_REMOTE_USER:-admin}"

# Used to set a default ssh multiplex. You can override it to disable it
export EXTRA_ANSIBLE_SSH_ARGS="${EXTRA_ANSIBLE_SSH_ARGS:-"-o ControlMaster=auto -o ControlPersist=60s"}"
export ANSIBLE_SSH_ARGS="${ANSIBLE_SSH_ARGS} ${EXTRA_ANSIBLE_SSH_ARGS}"
export ANSIBLE_FORCE_COLOR="${ANSIBLE_FORCE_COLOR:-true}"
export ANSIBLE_STDOUT_CALLBACK="${ANSIBLE_STDOUT_CALLBACK:-actionable}"

# Default envvars for aws_ec2
export AWS_INVENTORY="${AWS_INVENTORY:-auto}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-west-1}"
export AWS_REGION="${AWS_REGION:-$AWS_DEFAULT_REGION}" # Because some scripts use this variable instead of the default one
export AWS_EC2_COMPOSE_ANSIBLE_HOST="${AWS_EC2_COMPOSE_ANSIBLE_HOST:-private_ip_address}"
export AWS_EC2_TEMPLATE_FILE="${AWS_EC2_TEMPLATE_FILE:-/etc/ansible/hosts-template/default.aws_ec2.yml.template}"

# Default envvars for azure_rm.py
export DEFAULT_ANSIBLE_PLUGIN_AZURE_HOST="${DEFAULT_ANSIBLE_PLUGIN_AZURE_HOST:-"(public_dns_hostnames + public_ipv4_addresses + private_ipv4_addresses) | first"}"
export DEFAULT_ANSIBLE_PLUGIN_AZURE_HOST_PRIVATE="${DEFAULT_ANSIBLE_PLUGIN_AZURE_HOST_PRIVATE:-"(private_ipv4_addresses + public_dns_hostnames + public_ipv4_addresses) | first"}"
export AZURE_INVENTORY="${AZURE_INVENTORY:-auto}"
# Make sure args work for Ansible azure rm and https://raw.githubusercontent.com/ansible/ansible/devel/contrib/inventory/azure_rm.py
export AZURE_TENANT="${AZURE_TENANT:-$AZURE_TENANT_ID}"
export AZURE_USE_PRIVATE_IP="${AZURE_USE_PRIVATE_IP:-True}"
export AZURE_TEMPLATE_FILE="${AZURE_TEMPLATE_FILE:-/etc/ansible/hosts-template/default.azure_rm.yml.template}"
export ANSIBLE_PLUGIN_AZURE_PLAIN_HOST_NAMES="${ANSIBLE_PLUGIN_AZURE_PLAIN_HOST_NAMES:-False}"
export ANSIBLE_PLUGIN_AZURE_HOST="${ANSIBLE_PLUGIN_AZURE_HOST:-""}"

# Default envvars for gcp_compute
export GCP_INVENTORY="${GCP_INVENTORY:-auto}"
export GCP_USE_PRIVATE_IP="${GCP_USE_PRIVATE_IP:-True}"
export GCP_NETWORK_INTERFACE_IP="${GCP_NETWORK_INTERFACE_IP:-"networkInterfaces[0].networkIP"}"
export GCP_TEMPLATE_FILE="${GCP_TEMPLATE_FILE:-/etc/ansible/hosts-template/default.gcp_compute.yml.template}"

# Default envvars for vmware_vm_inventory
export VMWARE_VM_INVENTORY="${VMWARE_VM_INVENTORY:-auto}"
export VMWARE_PORT="${VMWARE_PORT:-443}"
export VMWARE_TEMPLATE_FILE="${VMWARE_TEMPLATE_FILE:-/etc/ansible/hosts-template/default.vmware.yml.template}"


#
# Construct vars
#

versionIsHigher() {
  printf '%s\n%s' "$1" "$2" | sort -rC -V
}

# actionnable callback is now deprecated: ERROR! [DEPRECATED]: community.general.actionable has been removed. Use the 'default' callback plugin with 'display_skipped_hosts = no' and 'display_ok_hosts = no' options. This feature was removed from community.general in version 2.0.0. Please update your playbooks.
# In order to keep a backward compatibility using the suggested variables with the default callback
if [ "$ANSIBLE_STDOUT_CALLBACK" == "actionable" ]; then
  if versionIsHigher "$ANSIBLE_VERSION" "2.8"; then
    export ANSIBLE_STDOUT_CALLBACK="default"
    export ANSIBLE_DISPLAY_OK_HOSTS="no"
    export ANSIBLE_DISPLAY_SKIPPED_HOSTS="no"
  fi
fi

if [ -n "$ANSIBLE_EXTRA_VARS" ]; then
  # This will read the whole file in a loop, then replaces the newline(s) with a \\n.
  echo "$ANSIBLE_EXTRA_VARS" | sed ':a;N;$!ba;s/\n/\\n/g' | jq -M . > /tmp/extra_ansible_args.json
  ANSIBLE_EXTRA_ARGS=" -e @/tmp/extra_ansible_args.json ${ANSIBLE_EXTRA_ARGS}"
fi
if [ -n "$TAGS" ]; then
  ANSIBLE_EXTRA_ARGS=" --tags $(echo $TAGS | jq -r '. | join(",")') ${ANSIBLE_EXTRA_ARGS}"
fi
if [ -n "$SKIP_TAGS" ]; then
  ANSIBLE_EXTRA_ARGS=" --skip-tags $(echo $SKIP_TAGS | jq -r '. | join(",")') ${ANSIBLE_EXTRA_ARGS}"
fi
if [ "$AWS_INVENTORY" == "auto" ] && [ -n "$AWS_ACCESS_KEY_ID" ] || [ "${AWS_INVENTORY,,}" == "true" ]; then
  # Render ec2.ini template from envvars
  envsubst < $AWS_EC2_TEMPLATE_FILE > /etc/ansible/hosts/aws_ec2.yml
  ANSIBLE_EXTRA_ARGS=" -i /etc/ansible/hosts/aws_ec2.yml ${ANSIBLE_EXTRA_ARGS}"
fi

if [ -z "${ANSIBLE_PLUGIN_AZURE_HOST}" ]; then
  if [ "${AZURE_USE_PRIVATE_IP,,}" == "true" ]; then
      export ANSIBLE_PLUGIN_AZURE_HOST="${DEFAULT_ANSIBLE_PLUGIN_AZURE_HOST_PRIVATE}"
  else
      export ANSIBLE_PLUGIN_AZURE_HOST="${DEFAULT_ANSIBLE_PLUGIN_AZURE_HOST}"
  fi
fi
if [ "$AZURE_INVENTORY" == "auto" ] && [ -n "$AZURE_SUBSCRIPTION_ID" ] || [ "${AZURE_INVENTORY,,}" == "true" ]; then
  if versionIsHigher "$ANSIBLE_VERSION" "2.8"; then
    # Render default.azure_rm.yml template from envvars
    envsubst < $AZURE_TEMPLATE_FILE > /etc/ansible/hosts/azure_rm.yml
    ANSIBLE_EXTRA_ARGS=" -i /etc/ansible/hosts/azure_rm.yml ${ANSIBLE_EXTRA_ARGS}"
  else
    cp /etc/ansible/hosts-template/azure_rm.py /etc/ansible/hosts/
    ANSIBLE_EXTRA_ARGS=" -i /etc/ansible/hosts/azure_rm.py ${ANSIBLE_EXTRA_ARGS}"
  fi
fi

if [ "$GCP_INVENTORY" == "auto" ] && [ -n "$GCP_SERVICE_ACCOUNT_CONTENTS" ] || [ "${GCP_INVENTORY,,}" == "true" ]; then
  if [ "${GCP_USE_PRIVATE_IP,,}" == "true" ]; then
      export GCP_NETWORK_INTERFACE_IP="networkInterfaces[0].networkIP"
  else
      export GCP_NETWORK_INTERFACE_IP="networkInterfaces[0].accessConfigs[0].natIP"
  fi
  export GCP_PROJECT=$(echo $GCP_SERVICE_ACCOUNT_CONTENTS | jq .project_id)
  export GCP_SERVICE_ACCOUNT_CONTENTS=$(echo $GCP_SERVICE_ACCOUNT_CONTENTS | tr '\n' ' ')
  # Render default.gcp_compute.yml template from envvars
  envsubst < $GCP_TEMPLATE_FILE > /etc/ansible/hosts/default.gcp_compute.yml
  ANSIBLE_EXTRA_ARGS=" -i /etc/ansible/hosts/default.gcp_compute.yml ${ANSIBLE_EXTRA_ARGS}"
fi

if [ "$VMWARE_VM_INVENTORY" == "auto" ] && [ -n "$VMWARE_SERVER" ] || [ "${VMWARE_VM_INVENTORY,,}" == "true" ]; then
  # Render default.vmware.yml template from envvars
  envsubst < $VMWARE_TEMPLATE_FILE > /etc/ansible/hosts/default.vmware.yml
  ANSIBLE_EXTRA_ARGS=" -i /etc/ansible/hosts/default.vmware.yml ${ANSIBLE_EXTRA_ARGS}"
fi

# Setup SSH access
eval $(ssh-agent -s)

# SSH keys
KEY_ID=1
if [ -n "$SSH_PRIVATE_KEYS" ]; then
	IFS=$'\n'
	for key in $(python -c "import json, os; print('\n'.join([ '%s' % v for v in json.loads(os.environ['SSH_PRIVATE_KEYS'].replace('\\n','\\\\\\\n'))]))"); do
		# Use the first key as default SSH_PRIVATE_KEY if not defined
		if [ -z "$SSH_PRIVATE_KEY" ]; then
			SSH_PRIVATE_KEY=$(echo -e $key)
			continue
		fi
		echo -e "$key" > /root/.ssh/id_rsa${KEY_ID}
		chmod 600 /root/.ssh/id_rsa${KEY_ID}
		ssh-add /root/.ssh/id_rsa${KEY_ID}
		KEY_ID=$((KEY_ID+1))
	done
	unset IFS
fi

if [ -n "$SSH_PRIVATE_KEY" ]; then
  # Root ssh key
  echo "${SSH_PRIVATE_KEY}" > /root/.ssh/id_rsa
  chmod 600  /root/.ssh/id_rsa
  ssh-add /root/.ssh/id_rsa
fi

# list ssh keys loaded
set +e
ssh-add -l
set -e

if [ -n "$SSH_JUMP_URL" ]; then
  export ANSIBLE_SSH_ARGS="$ANSIBLE_SSH_ARGS -o 'ProxyJump=$SSH_JUMP_URL' -o 'ForwardAgent=yes'"

# DEPRECATED jump parameter for a bastion server. Use SSH_JUMP_URL instead
elif [ -n "$BASTION_URL" ]; then
  export ANSIBLE_SSH_ARGS="$ANSIBLE_SSH_ARGS"' -o ProxyCommand="ssh -W %h:%p -q '${BASTION_URL}'"'
  #echo "ansible_ssh_common_args: '-o ProxyCommand=\"ssh -W %h:%p -q ${BASTION_URL}\"'" >> $ANSIBLE_PLAYBOOK_PATH/group_vars/all
fi

if [ -n "${ANSIBLE_LIMIT_HOSTS}" ]; then
	export ANSIBLE_EXTRA_ARGS=" --limit ${ANSIBLE_LIMIT_HOSTS} ${ANSIBLE_EXTRA_ARGS}"
fi
