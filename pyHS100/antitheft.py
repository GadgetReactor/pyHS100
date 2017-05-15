"""
pyHS100
Python library supporting TP-Link Smart Plugs/Switches (HS100/HS110/Hs200).

The communication protocol was reverse engineered by Lubomir Stroetmann and
Tobias Esser in 'Reverse Engineering the TP-Link HS110':
https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/

This library reuses codes and concepts of the TP-Link WiFi SmartPlug Client
at https://github.com/softScheck/tplink-smartplug, developed by Lubomir
Stroetmann which is licensed under the Apache License, Version 2.0.

You may obtain a copy of the license at
http://www.apache.org/licenses/LICENSE-2.0
"""


class AntiTheft(object):
    def __init__(self, _device, _query_helper):
        self._device = _device
        self._query_helper = _query_helper

    @property
    def _get_antitheft(self):
        """
        Gets all rules.

        :return: list rules
        :rtype: list
        :raises SmartPlugException: on error
        """

        return self._query_helper(
            "anti_theft",
            "get_rules"
        )

    def __iter__(self):
        """
        Iterates all rules.

        :return: iterator (name, rule)
        :rtype: iterator
        :raises SmartPlugException: on error
        """

        for antitheft in self._get_antitheft:
            yield antitheft['name'], antitheft

    def __contains__(self, name):
        """
        Checks if rule name exists.

        :param str name: name of the rule
        :return: bool True if name exists else False
        :rtype: bool
        :raises SmartPlugException: on error
        """

        for n, _ in self:
            if n == name:
                return True
        return False

    def __setitem__(self, name, rule):
        """
        Edits or Adds a new rule.

        If a rule exists with the same name it will be updated.
        Otherwise it will be added.

        Value must be a dict with the following key, value pairs
        "stime_opt":int(0)
        "wday":list(0, 1, 0, 1, 1, 0, 0), 0 or a 1 for each day of the week
                                          1 representing a scheduled day
        "smin":int(1014)
        "enable":int(1), 0 or a 1, 1 being enabled
        "frequency": int(5)
        "repeat": int(1), 0 or a 1, 1 to repeat the schedule
        "etime_opt": int(-1)
        "duration": int(2)
        "lastfor": int(1)
        "month": int(0), 0 for all months
        "year": int(0), 0 for all years
        "longitude": int/float(0), 0 for all locations
        "day": int(0), 0 for all days of the month
        "force": int(0), 0 or 1, 1 to force schedule
        "latitude": int/float(0), 0 for all locations
        "emin": int(0)

        :param str name: Name of the rule
        :param dict rule: Parameters for the rule (see description)
        :return: None
        :rtype: None
        :raises SmartPlugException: on error
        """

        if name in ('_device', '_query_helper'):
            object.__setattr__(self, name, rule)
            return

        rule['name'] = name

        if name in self:
            rule['id'] = self[name]['id']
            self._query_helper(
                "anti_theft",
                "edit_rule",
                rule
            )
        else:
            self._query_helper(
                "anti_theft",
                "add_rule",
                rule
            )

    def __delitem__(self, name):
        """
        Deletes rule.

        :param str name: Name of the rule
        :return: None
        :rtype: None
        :raises NoAntiTheftFound: If rule not found
        :raises SmartPlugException: on error
        """

        for n, a in self:
            if n == name:
                return self._query_helper(
                    "anti_theft",
                    "delete_rule",
                    {"id": a['id']}
                )
        raise NoAntiTheftFound(name)

    def get(self, name=None, *args):
        """
        Gets rule

        :param str name: Name of the rule.
        :param None name: If None returns all rules.
        :param args: Used for default return value.
        :return: dict name: All rules if item is None else rule
        :rtype: dict
        :raises NoAntiTheftFound: If rule not found
        :raises SmartPlugException: on error
        """

        if name is None:
            return dict(list(antitheft for antitheft in self))
        elif args and name not in self:
            return args[0]
        else:
            return self[name]

    def __getitem__(self, name):
        """
        Gets rule

        :param str name: Name of the rule.
        :return: dict rule
        :rtype: dict
        :raises NoAntiTheftFound: If rule not found
        :raises SmartPlugException: on error
        """

        if name in self.__dict__:
            return self.__dict__[name]

        for n, a in self:
            if n == name:
                return a

        raise NoAntiTheftFound(name)

    def __del__(self):
        """
        Deletes all rules.

        :return: None
        :rtype: None
        :raises SmartPlugException: on error
        """

        self._query_helper(
            "anti_theft",
            "delete_all_rules"
        )
        self._device.new_antitheft()


class NoAntiTheftFound(Exception):
    def __init__(self, name):
        self.msg = 'There is no antitheft by the name %s.' % name

    def __str__(self):
        return self.msg
