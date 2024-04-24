from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys

from ansible.plugins.callback import CallbackBase

DOCUMENTATION = """
name: failer
callback_type: aggregate
requirements:
- enable in configuration
short_description: Make ansible fail when no host found
description: |+
  This callback module exits non-zero if\n
  - No hosts are matched\n
  - No hosts are reachable\n
  - No step resulted in ["ok", "failure", "dark", "changed", "skipped"]

options: null
"""


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "aggregate"
    CALLBACK_NAME = "failer"
    CALLBACK_NEEDS_WHITELIST = False
    CALLBACK_NEEDS_ENABLED = True

    def __init__(self):
        super(CallbackModule, self).__init__()

    def playbook_on_no_hosts_matched(self):
        self.v2_playbook_on_no_hosts_matched()

    def playbook_on_stats(self, stats):
        self.v2_playbook_on_stats(stats)

    def runner_on_unreachable(self, host, res):
        self.v2_runner_on_unreachable()

    def v2_runner_on_unreachable(self):
        self._display.display("Failed due to host unreachable")
        sys.exit(1)

    def v2_playbook_on_no_hosts_matched(self):
        self._display.display("Failed due to no host matching")
        # raise AnsibleActionFail("Failed due to no host matching")
        sys.exit(1)

    def v2_playbook_on_stats(self, stats):
        found_stats = False

        for key in ["ok", "failures", "dark", "changed", "skipped"]:
            if len(getattr(stats, key)) > 0:
                found_stats = True
                break

        if not found_stats:
            self._display.display("Failed due to no stats")
            sys.exit(1)
