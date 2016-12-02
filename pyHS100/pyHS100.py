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

import datetime
import json
import logging
import socket
import sys

_LOGGER = logging.getLogger(__name__)

class SmartPlugException(Exception):
    pass

class SmartPlug:
    """Representation of a TP-Link Smart Switch.

    Usage example when used as library:
    p = SmartPlug("192.168.1.105")
    # print the devices alias
    print(p.alias)
    # change state of plug
    p.state = "OFF"
    p.state = "ON"
    # query and print current state of plug
    print(p.state)

    Note:
    The library references the same structure as defined for the D-Link Switch
    """
    # switch states
    SWITCH_STATE_ON = 'ON'
    SWITCH_STATE_OFF = 'OFF'
    SWITCH_STATE_UNKNOWN = 'UNKNOWN'

    # possible device features
    FEATURE_ENERGY_METER = 'ENE'
    FEATURE_TIMER = 'TIM'

    ALL_FEATURES = (FEATURE_ENERGY_METER, FEATURE_TIMER)

    def __init__(self, ip_address):
        """
        Create a new SmartPlug instance, identified through its IP address.

        :param ip_address: ip address on which the device listens
        """
        socket.inet_pton(socket.AF_INET, ip_address)
        self.ip_address = ip_address

        self.sys_info = self.get_sysinfo()

        self._alias, self.model, self.features = self.identify()

    def _query_helper(self, target, cmd, arg={}):
        """
        Query helper, raises SmartPlugException in case of failure, otherwise returns unwrapped result object

        :param target: Target system {system, time, emeter, ..}
        :param cmd:
        :param arg: JSON object passed as parameter to the command, defualts to {}
        :return: Unwrapped result for the call.
        :raises SmartPlugException if command was not executed correctly
        """
        response = TPLinkSmartHomeProtocol.query(
            host=self.ip_address,
            request={target: { cmd: arg }}
        )

        result = response[target][cmd]
        if result["err_code"] != 0:
            raise SmartPlugException("Error on %s.%s: %s" % (target, cmd, result))

        return result

    @property
    def state(self):
        """
        Retrieve the switch state

        :returns: one of
                  SWITCH_STATE_ON
                  SWITCH_STATE_OFF
                  SWITCH_STATE_UNKNOWN
        """
        relay_state = self.sys_info['relay_state']

        if relay_state == 0:
            return SmartPlug.SWITCH_STATE_OFF
        elif relay_state == 1:
            return SmartPlug.SWITCH_STATE_ON
        else:
            _LOGGER.warning("Unknown state %s returned.", relay_state)
            return SmartPlug.SWITCH_STATE_UNKNOWN

    @state.setter
    def state(self, value):
        """
        Set the new switch state

        :param value: one of
                    SWITCH_STATE_ON
                    SWITCH_STATE_OFF
        :return: True if new state was successfully set
                 False if an error occured
        """
        if value.upper() == SmartPlug.SWITCH_STATE_ON:
            self.turn_on()
        elif value.upper() == SmartPlug.SWITCH_STATE_OFF:
            self.turn_off()
        else:
            raise ValueError("State %s is not valid.", value)

    def get_sysinfo(self):
        """
        Retrieve system information.

        :return: dict sysinfo
        """

        return self._query_helper("system", "get_sysinfo")

    def turn_on(self):
        """
        Turn the switch on.

        :return: True on success
        :raises ProtocolError when device responds with err_code != 0
        """

        return self._query_helper("system", "set_relay_state", {"state": 1})

    def turn_off(self):
        """
        Turn the switch off.

        :return: True on success
                 False on error
        """

        return self._query_helper("system", "set_relay_state", {"state": 0})

    @property
    def has_emeter(self):
        """
        Checks feature list for energey meter support.

        :return: True if energey meter is available
                 False if energymeter is missing
        """
        return SmartPlug.FEATURE_ENERGY_METER in self.features

    def get_emeter_realtime(self):
        """
        Retrive current energy readings from device.

        :returns: dict with current readings
                  False if device has no energy meter or error occured
        """
        if not self.has_emeter:
            return False

        response = self._query_helper("emeter", "get_realtime")

        del response['err_code']

        return response

    def get_emeter_daily(self, year=None, month=None):
        """
        Retrieve daily statistics for a given month

        :param year: year for which to retrieve statistics (default: this year)
        :param month: month for which to retrieve statistcs (default: this
                      month)
        :return: dict: mapping of day of month to value
                 False if device has no energy meter or error occured
        """
        if not self.has_emeter:
            return False

        if year is None:
            year = datetime.datetime.now().year
        if month is None:
            month = datetime.datetime.now().month

        response = self._query_helper("emeter", "get_daystat", {'month': month, 'year': year})

        return {entry['day']: entry['energy']
                for entry in response['day_list']}

    def get_emeter_monthly(self, year=datetime.datetime.now().year):
        """
        Retrieve monthly statistics for a given year.

        :param year: year for which to retrieve statistics (default: this year)
        :return: dict: mapping of month to value
                 False if device has no energy meter or error occured
        """
        if not self.has_emeter:
            return False

        response = self._query_helper("emeter", "get_monthstat", {'year': year})

        return {entry['month']: entry['energy']
                for entry in response['month_list']}

    def erase_emeter_stats(self):
        """
        Erase energy meter statistics

        :return: True if statistics were deleted
                 False if device has no energy meter or error occured
        """
        if not self.has_emeter:
            return False

        response = self._query_helper("emeter", "erase_emeter_stat", None)

        return response['err_code'] == 0

    def current_consumption(self):
        """
        Get the current power consumption in Watt.

        :return: the current power consumption in Watt.
                 False if device has no energy meter of error occured.
        """
        if not self.has_emeter:
            return False

        response = self.get_emeter_realtime()

        return response['power']

    def identify(self):
        """
        Query device information to identify model and featureset

        :return: str model, list of supported features
        """
        alias = self.sys_info['alias']
        model = self.sys_info['model']
        features = self.sys_info['feature'].split(':')

        for feature in features:
            if feature not in SmartPlug.ALL_FEATURES:
                _LOGGER.warning("Unknown feature %s on device %s.",
                                feature, model)

        return alias, model, features

    @property
    def alias(self):
        """
        Get current device alias (name)
        :return:
        """
        return self._alias

    @alias.setter
    def alias(self, alias):
        """
        Sets the device name aka alias.
        :param alias: New alias (name)
        """

        self._query_helper("system", "set_dev_alias", {"alias": alias})

    @property
    def led(self):
        """
        Returns the state of the led.
        :return:
        """
        return {"led": 1 - self.sys_info["led_off"]}

    @led.setter
    def led(self, state):
        """
        Sets the state of the led (night mode)
        :param state: 1 to set led on, 0 to set led off
        """

        self._query_helper("system", "set_led_off", {"off": 1 - state})

    @property
    def icon(self):
        """
        Returns device icon
        Note: this doesn't seem to work when not using the cloud service, not tested with it either.
        :return:
        """
        return self._query_helper("system", "get_dev_icon")

    @icon.setter
    def icon(self, icon):
        """
        Content for hash and icon are unknown.
        :param icon:
        """

        raise SmartPlugNotImplementedException()

        self._query_helper("system", "set_dev_icon", {"icon": "", "hash": ""})

    @property
    def time(self):
        """
        Returns current time from the device.
        :return: datetime for device's time
        """

        response = self._query_helper("time", "get_time")
        ts = datetime.datetime(response["year"], response["month"], response["mday"], response["hour"], response["min"], response["sec"])

        return ts

    @time.setter
    def time(self, ts):
        """
        Sets time based on datetime object.
        Note, this calls set_timezone
        :param ts: New timestamp
        :return:
        """

        raise SmartPlugNotImplementedException("Setting time does not seem to work on HS110 although it returns no error.")

        ts_obj = {
            "index": self.timezone["index"],
            "hour": ts.hour,
            "min": ts.minute,
            "sec": ts.second,
            "year": ts.year,
            "month": ts.month,
            "mday": ts.day,
        }

        return self._query_helper("time", "set_timezone", ts_obj)

    @property
    def timezone(self):
        """
        Returns timezone information
        :return:
        """

        return self._query_helper("time", "get_timezone")

    @property
    def hw_info(self):
        """
        Returns information about hardware
        :return:
        """
        keys = ["sw_ver", "hw_ver", "mac", "hwId", "fwId", "oemId", "dev_name"]
        return {key:self.sys_info[key] for key in keys}

    @property
    def on_since(self):
        """
        Returns pretty-printed on-time
        :return:
        """
        return datetime.datetime.now() - datetime.timedelta(seconds=self.sys_info["on_time"])

    @property
    def location(self):
        """
        Location of the device, as read from sysinfo
        :return:
        """

        return {"latitude": self.sys_info["latitude"], "longitude": self.sys_info["longitude"]}

    @property
    def rssi(self):
        """
        Returns WiFi signal strenth (rssi)
        :return: rssi
        """

        return self.sys_info["rssi"]

    @property
    def mac(self):
        """
        Returns mac address
        :return:
        """
        return self.sys_info["mac"]

    @mac.setter
    def mac(self, mac):
        """
        Sets new mac address
        :param mac: mac in hexadecimal with colons, e.g. 01:23:45:67:89:ab
        """

        return self._query_helper("system", "set_mac_addr", {"mac": mac})


class TPLinkSmartHomeProtocol:
    """
    Implementation of the TP-Link Smart Home Protocol

    Encryption/Decryption methods based on the works of
    Lubomir Stroetmann and Tobias Esser

    https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/
    https://github.com/softScheck/tplink-smartplug/

    which are licensed under the Apache License, Version 2.0
    http://www.apache.org/licenses/LICENSE-2.0
    """
    initialization_vector = 171

    @staticmethod
    def query(host, request, port=9999):
        """
        Request information from a TP-Link SmartHome Device and return the
        response.

        :param host: ip address of the device
        :param port: port on the device (default: 9999)
        :param request: command to send to the device (can be either dict or
        json string)
        :return:
        """
        if isinstance(request, dict):
            request = json.dumps(request)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        _LOGGER.debug("> (%i) %s" % (len(request), request))
        sock.send(TPLinkSmartHomeProtocol.encrypt(request))
        buffer = bytes()
        while True:
            chunk = sock.recv(4096)
            buffer += chunk
            #_LOGGER.debug("Got chunk %s" % len(chunk))
            if len(chunk) == 0:
                break
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        response = TPLinkSmartHomeProtocol.decrypt(buffer[4:])
        _LOGGER.debug("< (%i) %s" % (len(response), response))
        return json.loads(response)

    @staticmethod
    def encrypt(request):
        """
        Encrypt a request for a TP-Link Smart Home Device.

        :param request: plaintext request data
        :return: ciphertext request
        """
        key = TPLinkSmartHomeProtocol.initialization_vector
        buffer = ['\0\0\0\0']

        for char in request:
            cipher = key ^ ord(char)
            key = cipher
            buffer.append(chr(cipher))

        ciphertext = ''.join(buffer)
        if sys.version_info.major > 2:
            ciphertext = ciphertext.encode('latin-1')

        return ciphertext

    @staticmethod
    def decrypt(ciphertext):
        """
        Decrypt a response of a TP-Link Smart Home Device.

        :param ciphertext: encrypted response data
        :return: plaintext response
        """
        key = TPLinkSmartHomeProtocol.initialization_vector
        buffer = []

        if sys.version_info.major > 2:
            ciphertext = ciphertext.decode('latin-1')

        for char in ciphertext:
            plain = key ^ ord(char)
            key = ord(char)
            buffer.append(chr(plain))

        plaintext = ''.join(buffer)

        return plaintext
