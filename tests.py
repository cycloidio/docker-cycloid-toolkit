#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from os.path import join as osjoin
import unittest2 as unittest
import json
import shutil
import os, sys
import subprocess
from distutils.util import strtobool
import time
import re

import docker


# Run tests :
# virtualenv -p python3 --clear .env
# source .env/bin/activate
# pip install unittest2 docker
# 
# python tests.py

# Debug print command that you can use
# print(r.output.decode('utf-8'))


class TestCase(unittest.TestCase):

    def drun(self, *args, **kwargs):
        kwargs['tty'] = True
        kwargs['stdin'] = True
        return self.container.exec_run(*args, **kwargs)

    def file_list(self, path):
        r = self.drun(cmd="find %s -type f -printf '%%P\n'" % path)
        return sorted([line for line in r.output.decode('utf-8').split('\r\n') if line != ''])

    def output_contains(self, output, pattern):
        p = re.compile(pattern)

        for line in output.decode('utf-8').split('\r\n'):
            if p.match(line):
                return True
        return False

    def setup_dir(self):
        if os.path.exists(self.testsdir):
            shutil.rmtree(self.testsdir)
        shutil.copytree('tests', self.testsdir)

    def clean_dir(self):
        if os.path.isdir(self.testsdir):
            shutil.rmtree(self.testsdir)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker = docker.from_env()
        self.docker_image = os.environ.get('IMAGE_NAME', 'cycloid/cycloid-toolkit')
        self.testsdir = "/tmp/%s" % self.__class__.__name__
        self.clean_dir()

    def setUp(self):
        super().setUp()
        self.setup_dir()

    def tearDown(self):
        super().tearDown()
        self.container.kill()
        try:
            self.container.wait(condition='removed')
        except docker.errors.NotFound:
            pass
        self.clean_dir()


class MergeStackAndConfigTestCase(TestCase):

    def setUp(self):
        super().setUp()
        environment={
            'STACK_ROOT_PATH': 'stack',
            'CONFIG_ROOT_PATH': 'config',
            'MERGE_OUTPUT_PATH': '/tmp/merged-stack',
        }
        self.container = self.docker.containers.run(image=self.docker_image,
                                   command='sleep 3600',
                                   name=self.__class__.__name__,
                                   auto_remove=True,
                                   remove=True,
                                   detach=True,
                                   working_dir='/opt',
                                   volumes={osjoin(os.getcwd(), '%s/merge-stack-and-config' % self.testsdir): {'bind': '/opt', 'mode': 'rw'}},
                                   environment=environment,
                                  )


    def test_required_args(self):
        environment={
            'STACK_PATH': 'fake/directory',
            'CONFIG_PATH': 'fake/directory',
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ERROR : the stack directory'))
        self.assertEquals(r.exit_code, 1)

    def test_basic(self):

        # Can run without good config path (display warning)
        environment={
            'CONFIG_PATH': 'fake/directory',
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*Warning, CONFIG_PATH if not configured'))
        self.assertEquals(r.exit_code, 0)
        files = self.file_list("/tmp/merged-stack")
        self.assertEquals(['foo/bar', 'stack-file'], files)

        # regular run
        r = self.drun(cmd="/usr/bin/merge-stack-and-config")
        self.assertEquals(r.exit_code, 0)
        files = self.file_list("/tmp/merged-stack")
        self.assertEquals(['config-file', 'foo/bar', 'stack-file'], files)

        # Regular run but override one file from config
        environment={
            'CONFIG_ROOT_PATH': 'config-override',
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        files = self.file_list("/tmp/merged-stack")
        self.assertEquals(['config-file', 'foo/bar', 'stack-file'], files)
        r = self.drun(cmd="cat /tmp/merged-stack/stack-file")
        self.assertTrue(self.output_contains(r.output, 'File from config'))


    def test_subdirectories(self):
        # Ensure sub directories produce the expected merged stack directory
        environment={
            'CONFIG_PATH': 'config',
            'STACK_PATH': 'stack',
            'STACK_ROOT_PATH': '.',
            'CONFIG_ROOT_PATH': '.',
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertEquals(r.exit_code, 0)
        files = self.file_list("/tmp/merged-stack")
        self.assertEquals(['config-file', 'foo/bar', 'stack-file'], files)

    def test_extra_paths(self):
        # Merge stack and config + extra paths (unvalid valid directory)
        environment={
            'EXTRA_PATH': '["fake/directory"]',
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertEquals(r.exit_code, 0)
        self.assertTrue(self.output_contains(r.output, '.*Warning, the extra directory'))

        # Merge stack and config + extra paths
        environment={
            'EXTRA_PATH': '["extra-path1/", "extra-path2/"]',
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertEquals(r.exit_code, 0)
        files = self.file_list("/tmp/merged-stack")
        self.assertEquals(['1', '2', 'config-file', 'foo/bar', 'stack-file'], files)


    def test_extra_ansible_vars(self):
        # Merge stack and config + extra paths
        environment={
            'EXTRA_ANSIBLE_VARS': "{\"severallines\": \"line1\nline2\", \"foo\": \"bar\"}",
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertEquals(r.exit_code, 0)
        r = self.drun(cmd="cat /tmp/merged-stack/group_vars/all")
        self.assertTrue(self.output_contains(r.output, 'foo: "bar"'))
        # Looking for "line1\nline2" but had to escape it
        self.assertTrue(self.output_contains(r.output, 'severallines: "line1\\\\nline2"'))


    def test_terraform_metadata(self):
        environment={
            'TERRAFORM_METADATA_FILE': 'terraform-data/metadata',
        }
        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertEquals(r.exit_code, 0)
        r = self.drun(cmd="cat /tmp/merged-stack/group_vars/all")
        self.assertTrue(self.output_contains(r.output, 'terraform: output'))



    def test_git_tag_file(self):
        # If not git, don't extract tags
        r = self.drun(cmd="/usr/bin/merge-stack-and-config")
        self.assertEquals(r.exit_code, 0)

        r = self.drun(cmd="ls /tmp/merged-stack/tag")
        self.assertEquals(r.exit_code, 1)

        environment={
            'STACK_ROOT_PATH': '/tmp/stack',
            'CONFIG_ROOT_PATH': '/tmp/config',
        }
        # Creating git repo and a commit for stack and config
        # It should extract commit in a tag file
        r = self.drun(cmd=("bash -c 'git init /tmp/stack &&"
                           " echo stack > /tmp/stack/file &&"
                           " git --work-tree=/tmp/stack  --git-dir=/tmp/stack/.git config user.name John &&"
                           " git --work-tree=/tmp/stack  --git-dir=/tmp/stack/.git config user.email john@doe.org &&"
                           " git --work-tree=/tmp/stack  --git-dir=/tmp/stack/.git add file &&"
                           " git --work-tree=/tmp/stack  --git-dir=/tmp/stack/.git add file &&"
                           " git --work-tree=/tmp/stack  --git-dir=/tmp/stack/.git commit -m tests'"))
        r = self.drun(cmd=("bash -c 'git init /tmp/config &&"
                           " echo config > /tmp/config/file &&"
                           " git --work-tree=/tmp/config  --git-dir=/tmp/config/.git config user.name John &&"
                           " git --work-tree=/tmp/config  --git-dir=/tmp/config/.git config user.email john@doe.org &&"
                           " git --work-tree=/tmp/config  --git-dir=/tmp/config/.git add file &&"
                           " git --work-tree=/tmp/config  --git-dir=/tmp/config/.git add file &&"
                           " git --work-tree=/tmp/config  --git-dir=/tmp/config/.git commit -m tests'"))

        r = self.drun(cmd="/usr/bin/merge-stack-and-config", environment=environment)
        self.assertEquals(r.exit_code, 0)

        r = self.drun(cmd="ls /tmp/merged-stack/tag")
        self.assertEquals(r.exit_code, 0)
        self.assertTrue(self.output_contains(r.output, '[^-]+-[^-]+'))


class AnsibleRunnerTestCase(TestCase):

    def setUp(self):
        super().setUp()
        environment={
            'SSH_PRIVATE_KEY': '''-----BEGIN RSA PRIVATE KEY-----
MIICWgIBAAKBgQC6W6OIBOiewkaKBz73bQkv0dqfiUEOrNI0+zWEc3SaaLhz8k1k
Nug+K+0nEh4GbP82wx+1bLd+KeJUg4EX4kmgHY8Yg8aLkcbSC6kMMqfrRsN2HG4W
DqRrBvWiTTbEZQB+K6fOhmOFLcI+jkYAgBiPx4YjLIZsV+6+WyG9/ODPiwIDAQAB
An9GnHJaF4IMpZAUvKofFjFk7R7pVBhSdyku6gBdL2H/H67EQAsS7bsR05MIOtUl
micZmNVq6MaeB0C6xRkk85jxbJvx4kuBkXVuckFLx2Bij7a+tJavlprkfEOw2hja
EP27ChGnX3HuCGuQ6NqBXooNBYT0c34z4Io3sREHAzuxAkEA4xslTeLV+JXYzbqW
C+sZmN7PJg1XBuNJIiYFSx7uFBEW4jLD7n8lbm0SmHd1EGVlaMNahHPqAHB/OQod
a/cFAwJBANIRU479ElSqYGuf92Gp6ZiE1Vxs6MpJGbzPJfAtu343MmxLn9w/8kel
Z8p4/vjRugtxCBMYs4JmPoWhmxQvMNkCQEnU92m8xwdL3/HyKPmy8t1qAjpCt/o7
RfleFvZ3FbtcWu4qxtvwZgDiYNtEasBr1m4apIDPFlISQKoQicQhyHUCQGiUjafr
H9wcskICcpMhlxUCVIJeCgrjF7gi3L1U1zn/2s+FWsG46DJ5C1IGqNFRADFABYgU
TRIHOusmSGFlGQkCQQC4mLnzDbfgBGAkB6HsGTvdsxElQ+s+h9RlHlg/PxdiKBVI
j/McHvs4QerVnwQYfoRaNpFdQwNxL96tYM5M/5jH
-----END RSA PRIVATE KEY-----''',
            'ANSIBLE_PLAYBOOK_PATH': 'playbook',
            'ANSIBLE_FORCE_COLOR': 'false',
            'ANSIBLE_VAULT_PASSWORD': 'password',
            'ANSIBLE_NOCOLOR': 'true',
        }
        self.container = self.docker.containers.run(image=self.docker_image,
                                   command='sleep 3600',
                                   name=self.__class__.__name__,
                                   auto_remove=True,
                                   remove=True,
                                   detach=True,
                                   working_dir='/opt',
                                   volumes={osjoin(os.getcwd(), '%s/ansible-runner' % self.testsdir): {'bind': '/opt', 'mode': 'rw'}},
                                   environment=environment,
                                  )
        r = self.drun(cmd="python -c \"import sys; print('%s.%s' % (sys.version_info.major, sys.version_info.minor))\"")
        self.python_version = r.output.decode('utf-8').rstrip()

        r = self.drun(cmd="python -c \"from ansible.cli import CLI; print('%d.%d' % (CLI.version_info().get('major'), CLI.version_info().get('minor')))\"")
        self.ansible_version = r.output.decode('utf-8').rstrip()

    def test_ansible_galaxy(self):
        # Run ansible galaxy
        environment={
            'ANSIBLE_PLAYBOOK_PATH': 'galaxy',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*galaxy'))
        self.assertEquals(r.exit_code, 0)

        # Try a force run of ansible galaxy
        environment={
            'ANSIBLE_PLAYBOOK_PATH': 'galaxy',
            'ANSIBLE_FORCE_GALAXY': 'true',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*galaxy.*--force'))
        self.assertEquals(r.exit_code, 0)

    def test_basic(self):
        environment={
            'EXTRA_ANSIBLE_VARS': '',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ansible-playbook -u admin'))
        self.assertEquals(r.exit_code, 0)

        # Test PRIVATE_SSH_KEY
        r = self.drun(cmd="cat /root/.ssh/id_rsa")
        self.assertTrue(self.output_contains(r.output, '^-----BEGIN RSA PRIVATE KEY-----'))
        self.assertTrue(self.output_contains(r.output, '^MIICWgIBAAKBgQC6W6OIBOiewka'))
        self.assertTrue(self.output_contains(r.output, '^-----END RSA PRIVATE KEY-----'))

        # Test SSH_PRIVATE_KEYS
        environment={
            'SSH_PRIVATE_KEY': '',
            'SSH_PRIVATE_KEYS': '''["-----BEGIN RSA PRIVATE KEY-----\nMIICWwIBAAKBgQCsZ1ao/9WyCzU7x843xbfI1aH/JdHWxNbEYrcceddNUBpEFu5m\nE8OakHADydCAd2KoYnWuPNb7Je433/b3YYimgOgKIZ46Y//RHqcyscu+v/zXDFUM\nXtMd00Qt/rtFgGGN1iLNS/XTqwKMU8ZJuAiKTg5YAp3Nc9h8ksEWRmnO1QIDAQAB\nAoGAAb8qSZwN9jfW2jw0AqymKArCEWu4rIxiAKtfX5J8c/QT0AzLbY1VtgMwn1k0\nG5kaDsqwlotXQkQoHbjPL8J1N/ZgNTjOvANLqFiAv0rU/2iko2gzHke7PLJYIWon\nFdHTes2qPVwkdRjdCTZDTIKZTF3rFdWfBNXUn2xdJCYoOAECQQDlweRhR7t0YWCk\nneR8yYGjEAbqJrF5uuGAOdMshgzsWeQV2yqXCDJItRoCFfnRQJ0CH+k9tC0wZbH/\nsga/kkZBAkEAwBhsTLEq4FMC67xGqI9BG11fO2ygvGnOOIEx2C8QIWiTuCq11ifB\nQqMCAtdW4XUMcSeWl9xXdDxU/UA2WforlQJAQcWMpFCNmBZcPSO6CgMBanWnFRa4\njZly/msPSdqiDnL5OUyBV7UP+AJoDJrP5hgyGi6abYCLwyQJnaIQDn1IQQJALYCb\nhr8gzOpc8sIyapMkdPr1J/pfSMI3WyMfT3o2c/N1qlZTpFreaI58V3fy2I0FWXhr\nL6W+AYaZCzQ+q6ma0QJATjW1WRs3EdeVei96fqyU6cbq2vMoyU4UlZMmxU8oWhVG\ngoaHVf9crFoEuUYL9QNG28OJYbyQo5u+MaVrcT/l0A==\n-----END RSA PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDAn7Kv6B/IPi+cV0WAMm6RYarDG6p4c5EMaHgpIvt0TU4KzHcR\npgXjjIKBJdYlVYtkb7xuCsJKHOqq5jFMSEhw2mCJtvnGADJdx8wNQZiUcOzVixYp\nJw+47clp15ApxxYmkKSgEynZsbIKuWDZaMX6eZ4PFR4G8kFB1x6YnSDPkQIDAQAB\nAoGAOUOAoJDWWfY6uzSqobjca/XoCQbBf/uDRHgOONSAgou0xrsQLrv3hjUwWup/\npiuvO9WH5ALozZWZIeM7Bp16gyUVUA4B4TRCA0cgs64zhJBUhlRzAa8EWUkTimjN\n7VjpnM2lfsRpDzBRHiFNvK71JGEtoxKla+9wO+7cCuFeu/0CQQD8tmCKIg0c+3K3\ntupKwPtSZ2JlLQ0mWol/EEPknJZDGc8dOQpic7yscw8S0PsX+dRP/2W+DaLiWQYS\n0Rc/dBxbAkEAwyE0UDqHmVBxCG+AI4prOXF7YxI/d2XbcC8cFvna4RFNl7v+d5h2\nYN1m6tMDIw+C/XUIIDnJSrsvkmzH+Rh3gwJBAIW6HKv8CORlSvdcm+6i4Ftiyfaw\nOF0rW8cZXFQFaJ5pcegM3ynqBNVcrYVPgQ/W7DrI85X2sVMFuOkMLDkvwDECQH9E\nENKi2f3ssUxHLNQBW53Dni4noK1HCbBJiZCStWdF2c21F2r5TXwv6wgNSGZ9n3mf\n8wTRq6/KFmTx/htBEfECQHfDWbA5hfnpsN3HbAO+Hcv6oBEY7CEOTB2Jcw6jnKR3\n/AT0NXdfaGORivBUiFk6jq1za8KfiXz6ipLzrSnnPZ0=\n-----END RSA PRIVATE KEY-----"]''',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        r = self.drun(cmd="cat /root/.ssh/id_rsa")
        self.assertTrue(self.output_contains(r.output, '^MIICWwIBAAKBgQCsZ1ao'))

        r = self.drun(cmd="cat /root/.ssh/id_rsa1")
        self.assertTrue(self.output_contains(r.output, '^MIICXAIBAAKBgQDAn7Kv6B'))

        r = self.drun(cmd="cat playbook/.vault-password")
        self.assertTrue(self.output_contains(r.output, '.*password'))
    

    def test_extra_args(self):
        environment={
            'TAGS': '["foo", "bar"]',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*--tags foo,bar'))
        self.assertEquals(r.exit_code, 0)

        environment={
            'SKIP_TAGS': '["foo", "bar"]',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*--skip-tags foo,bar'))
        self.assertEquals(r.exit_code, 0)

        environment={
            'EXTRA_ANSIBLE_VARS': '{"foo":"value 1","bar": 42}',
            'EXTRA_ANSIBLE_ARGS': '-vvv',
            'ANSIBLE_STDOUT_CALLBACK': 'minimal',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-e @/tmp/extra_ansible_args.json'))
        self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-vvv'))
        self.assertTrue(self.output_contains(r.output, '.*"msg": "hello 42"'))
        self.assertEquals(r.exit_code, 0)

        r = self.drun(cmd="cat /tmp/extra_ansible_args.json")
        self.assertTrue(self.output_contains(r.output, '.*bar.+42'))

    def test_ssh_jumps_args(self):
        environment={
            'BASTION_URL': 'root@localhost',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ANSIBLE_SSH_ARGS.*root@localhost'))
        self.assertEquals(r.exit_code, 0)

        environment={
            'BASTION_URL': 'root@localhost',
            'SSH_JUMP_URL': 'admin@bastion1,admin@bastion2',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ProxyJump=admin@bastion1,admin@bastion2'))
        self.assertEquals(r.exit_code, 0)

    def test_ec2_hosts_inventory(self):
        # default vpc_destination_variable should be private_ip_address
        # EC2 dynamic inventory should not be used as AWS_INVENTORY default to auto and AWS_ACCESS_KEY_ID is not present
        r = self.drun(cmd="/usr/bin/ansible-runner")
        self.assertFalse(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/ec2.py'))
        self.assertEquals(r.exit_code, 0)

        # assert that no ec2 inventory will be loaded from /etc/ansible/hosts
        self.assertFalse(os.path.exists("/etc/ansible/hosts/ec2.ini"))
        # vpc_destination_variable should be ip_address
        # EC2 dynamic inventory should be used as AWS_INVENTORY default to auto and AWS_ACCESS_KEY_ID is present
        environment={
            'AWS_ACCESS_KEY_ID': 'foo',
            'EC2_VPC_DESTINATION_VARIABLE': 'ip_address',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/ec2.py'))
        self.assertEquals(r.exit_code, 0)

        r = self.drun(cmd="cat /etc/ansible/hosts/ec2.ini")
        self.assertTrue(self.output_contains(r.output, '^vpc_destination_variable .+ip_address'))

        # EC2 dynamic inventory should be used as AWS_INVENTORY=true even if AWS_ACCESS_KEY_ID is not present
        environment={
            'AWS_INVENTORY': 'true',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/ec2.py'))
        self.assertEquals(r.exit_code, 0)

        # EC2 dynamic inventory should not be used as AWS_INVENTORY=false even if AWS_ACCESS_KEY_ID is present
        environment={
            'AWS_INVENTORY': 'false',
            'AWS_ACCESS_KEY_ID': 'foo',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertFalse(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/ec2.py'))
        self.assertEquals(r.exit_code, 0)

    def test_azure_hosts_inventory(self):
        # Azure dynamic inventory should not be used as AZURE_INVENTORY defaults to auto and AZURE_SUBSCRIPTION_ID is not present
        r = self.drun(cmd="/usr/bin/ansible-runner")
        self.assertFalse(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/azure_rm.py'))
        self.assertFalse(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/default.azure_rm.yml'))
        self.assertEquals(r.exit_code, 0)

        # Azure dynamic inventory should be used as AZURE_INVENTORY defaults to auto and AZURE_SUBSCRIPTION_ID is present
        environment={
            'AZURE_SUBSCRIPTION_ID': 'foo',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        if float(self.ansible_version) >= 2.7:
            self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/default.azure_rm.yml'))
        else:
            self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/azure_rm.py'))
        self.assertEquals(r.exit_code, 0)

        # Azure dynamic inventory should be used as AZURE_INVENTORY=true even if AZURE_SUBSCRIPTION_ID is not present
        environment={
            'AZURE_INVENTORY': 'true',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        if float(self.ansible_version) >= 2.7:
            self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/default.azure_rm.yml'))
        else:
            self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/azure_rm.py'))
        self.assertEquals(r.exit_code, 0)

        # Azure dynamic inventory should not be used as AZURE_INVENTORY=false even if AZURE_SUBSCRIPTION_ID is present
        environment={
            'AZURE_INVENTORY': 'false',
            'AZURE_SUBSCRIPTION_ID': 'foo',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertFalse(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/azure_rm.py'))
        self.assertFalse(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/default.azure_rm.yml'))
        self.assertEquals(r.exit_code, 0)

    def test_ec2_and_azure_hosts_inventory(self):
        # EC2 dynamic inventory should be used as AWS_INVENTORY defaults to auto and AWS_ACCESS_KEY_ID is present
        # Azure dynamic inventory should be used as AZURE_INVENTORY defaults to auto and AZURE_SUBSCRIPTION_ID is present
        environment={
            'AZURE_SUBSCRIPTION_ID': 'foo',
            'AWS_ACCESS_KEY_ID': 'bar',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        if float(self.ansible_version) >= 2.7:
            self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/ec2.py.*-i /etc/ansible/hosts/default.azure_rm.yml'))
        else:
            self.assertTrue(self.output_contains(r.output, '.*ansible-playbook.*-i /etc/ansible/hosts/ec2.py.*-i /etc/ansible/hosts/azure_rm.py'))
        self.assertEquals(r.exit_code, 0)

if __name__ == '__main__':
    unittest.main()
