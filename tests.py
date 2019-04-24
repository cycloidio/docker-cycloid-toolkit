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


#        self.clean_dir()
#        os.makedirs(self.testdir)
class TestCase(unittest.TestCase):

    def drun(self, *args, **kwargs):
        kwargs['tty'] = True
        kwargs['stdin'] = True
        return self.container.exec_run(*args, **kwargs)

    def file_list(self, path):
        r = self.drun(cmd="find %s -type f -printf '%%P\n'" % path)
        return sorted([line for line in r.output.decode('utf-8').split('\r\n') if line != ''])

    #def run_cmd(self, cmd):
    #    stdout = subprocess.Popen('%s 2>/dev/null' % cmd,
    #                              shell=True,
    #                              stdout=subprocess.PIPE)
    #    return [line for line in stdout.communicate()[0].split('\r\n') if line != '']

    def output_contains(self, output, pattern):
        p = re.compile(pattern)

        for line in output.decode('utf-8').split('\r\n'):
            if p.match(line):
                return True
        return False

    def clean_dir(self):
        if os.path.isdir(self.testdir):
            shutil.rmtree(self.testdir)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker = docker.from_env()
        #self.use_docker = strtobool(os.getenv('USE_DOCKER', 'true'))

    def tearDown(self):
        super().tearDown()
        self.container.kill()
        try:
            self.container.wait(condition='removed')
        except docker.errors.NotFound:
            pass


class MergeStackAndConfigTestCase(TestCase):

    def setUp(self):
        super().setUp()
        environment={
            'STACK_ROOT_PATH': 'stack',
            'CONFIG_ROOT_PATH': 'config',
            'MERGE_OUTPUT_PATH': '/tmp/merged-stack',
        }
        self.container = self.docker.containers.run(image='cycloid/cycloid-toolkit',
                                   command='sleep 3600',
                                   name=self.__class__.__name__,
                                   auto_remove=True,
                                   remove=True,
                                   detach=True,
                                   working_dir='/opt',
                                   volumes={osjoin(os.getcwd(), 'tests/merge-stack-and-config'): {'bind': '/opt', 'mode': 'rw'}},
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
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'SSH_PRIVATE_KEY': '''-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQEA3gH0VocXkTRHxgMAcNRgZfe1y1OC+MtJ3vmkX3K28A7FgCE7
-----END RSA PRIVATE KEY-----''',
            'ANSIBLE_PLAYBOOK_PATH': 'playbook',
            'ANSIBLE_FORCE_COLOR': 'false',
            'ANSIBLE_VAULT_PASSWORD': 'password',
            'ANSIBLE_NOCOLOR': 'true',
        }
        self.container = self.docker.containers.run(image='cycloid/cycloid-toolkit',
                                   command='sleep 3600',
                                   name=self.__class__.__name__,
                                   auto_remove=True,
                                   remove=True,
                                   detach=True,
                                   working_dir='/opt',
                                   volumes={osjoin(os.getcwd(), 'tests/ansible-runner'): {'bind': '/opt', 'mode': 'rw'}},
                                   environment=environment,
                                  )

    def test_required_args(self):
        environment={
            'AWS_ACCESS_KEY_ID': '',
            'AWS_SECRET_ACCESS_KEY': '',
            'SSH_PRIVATE_KEY': '',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertEquals(r.exit_code, 1)

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

        r = self.drun(cmd="cat /root/.ssh/id_rsa")
        self.assertTrue(self.output_contains(r.output, '^-----BEGIN RSA PRIVATE KEY-----'))
        self.assertTrue(self.output_contains(r.output, '^-----END RSA PRIVATE KEY-----'))

        r = self.drun(cmd="cat playbook/.vault-password")
        self.assertTrue(self.output_contains(r.output, '.*password'))
    

    def test_extra_args(self):
        environment={
            'BASTION_URL': 'root@localhost',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertTrue(self.output_contains(r.output, '.*ANSIBLE_SSH_ARGS.*root@localhost'))
        self.assertEquals(r.exit_code, 0)

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




    def test_ec2_hosts_inventory(self):
        r = self.drun(cmd="/usr/bin/ansible-runner")
        r = self.drun(cmd="cat /etc/ansible/hosts/ec2.ini")
        self.assertTrue(self.output_contains(r.output, '^vpc_destination_variable .+private_ip_address'))

        environment={
            'EC2_VPC_DESTINATION_VARIABLE': 'ip_address',
        }
        r = self.drun(cmd="/usr/bin/ansible-runner", environment=environment)
        self.assertEquals(r.exit_code, 0)

        r = self.drun(cmd="cat /etc/ansible/hosts/ec2.ini")
        self.assertTrue(self.output_contains(r.output, '^vpc_destination_variable .+ip_address'))













    

#    def test_ls(self):
#        # Test ls without files
#        rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
#        self.assertEquals('200 OK', rv.status)
#        self.assertEquals(json.loads(rv.get_data()), {})
#
#        # With one posted file
#        _file = osjoin(self.testdir, 'test_file')
#        last_file_md5 = write_random_file(_file)  # keep md5 for next test
#        rv = self.app.post('/', data={'file': (open(_file, 'r'),
#                           'test_pastefile_random.file'), })
#        rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
#        self.assertEquals('200 OK', rv.status)
#        # basic check if we have an array like {md5: {name: ...}}
#        filenames = [infos['name'] for md5, infos in json.loads(
#            rv.get_data()).iteritems()]
#        self.assertEquals(['test_pastefile_random.file'], filenames)
#
#        # Add one new file.
#        # Remove the first file from disk only in the last test
#        os.remove(osjoin(flaskr.app.config['UPLOAD_FOLDER'], last_file_md5))
#        _file = osjoin(self.testdir, 'test_file_2')
#        write_random_file(_file)
#        rv = self.app.post('/', data={'file': (open(_file, 'r'),
#                           'test_pastefile2_random.file'), })
#        rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
#        filenames = [infos['name'] for md5, infos in json.loads(
#            rv.get_data()).iteritems()]
#        self.assertEquals(['test_pastefile2_random.file'], filenames)
#
#        # if we lock the database, get should work
#        with mock.patch('pastefile.controller.JsonDB._lock',
#                        mock.Mock(return_value=False)):
#            rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
#        self.assertEquals(['test_pastefile2_random.file'], filenames)
#
#        # Try with ls disables
#        flaskr.app.config['DISABLED_FEATURE'] = ['ls']
#        rv = self.app.get('/ls', headers={'User-Agent': 'curl'})
#        self.assertEquals(rv.get_data(),
#                          'Administrator disabled the /ls option.\n')


if __name__ == '__main__':
    unittest.main()

