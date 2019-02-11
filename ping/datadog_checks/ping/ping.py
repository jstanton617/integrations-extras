# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.checks import AgentCheck
from datadog_checks.utils.subprocess_output import get_subprocess_output
from datadog_checks.errors import CheckException
import platform
import re


class PingCheck(AgentCheck):

    SERVICE_CHECK_NAME = 'network.ping.can_connect'

    def _load_conf(self, instance):
        # Fetches the conf

        timeout = float(instance.get('timeout', 4))
        response_time = instance.get('collect_response_time', False)
        custom_tags = instance.get('tags', [])

        host = instance.get('host', None)
        if host is None:
            raise CheckException("A valid host must be specified")

        return host, custom_tags, timeout, response_time

    def _exec_ping(self, timeout, target_host):
        if platform.system() == "Windows":
            countOption = "-n"
            timeoutOption = "-w"
        else:
            countOption = "-c"
            timeoutOption = "-W"

        self.log.debug("pinging {} {} {} {} {}".format(countOption, "1", timeoutOption, str(int(timeout)*1000), target_host))

        lines, err, retcode = get_subprocess_output(
            ["ping", countOption, "1", timeoutOption, str(int(timeout)*1000), target_host],
            self.log, raise_on_empty_output=True)
        self.log.debug("ping returned {} - {} - {}".format(retcode, lines, err))
        if retcode != 0:
            raise CheckException("ping returned {}: {}".format(retcode, err))

        return lines

    def check(self, instance):
        host, custom_tags, timeout, response_time = self._load_conf(instance)

        custom_tags.append('target_host:{}'.format(host))
        custom_tags.append('instance:{}'.format(instance.get('name')))


        try:
            lines = self._exec_ping(timeout, host)

            regex = re.compile(r"time=((\d|\.)*)")

            length = None

            result = regex.findall(lines)
            if result:
                length = result[0][0]
            else:
                raise CheckException("No time= found ({})".format(lines))

        except Exception as e:
            self.log.info("{} is DOWN ({})".format(host, str(e)))
            self.service_check(self.SERVICE_CHECK_NAME,
                               AgentCheck.CRITICAL,
                               custom_tags,
                               message=str(e))
            self.gauge(self.SERVICE_CHECK_NAME, 0, custom_tags)

            return

        if response_time:
            self.gauge('network.ping.response_time', length, custom_tags)

        self.log.debug("{} is UP".format(host))
        self.service_check(self.SERVICE_CHECK_NAME,
                           AgentCheck.OK,
                           custom_tags,
                           "")
        self.gauge(self.SERVICE_CHECK_NAME, 1, custom_tags)