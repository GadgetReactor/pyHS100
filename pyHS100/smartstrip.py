import datetime
import logging
from typing import Any, Dict, Optional

from pyHS100 import SmartDevice

_LOGGER = logging.getLogger(__name__)


class SmartStrip(SmartDevice):
    """Representation of a TP-Link Smart Power Strip.

    Usage example when used as library:
    p = SmartStrip("192.168.1.105")
    # print the devices alias
    print(p.alias)
    # change state of plug
    p.state = "ON"
    p.state = "OFF"
    # query and print current state of plug
    print(p.state)

    Errors reported by the device are raised as SmartDeviceExceptions,
    and should be handled by the user of the library.

    Note:
    The library references the same structure as defined for the D-Link Switch
    """
    # switch states
    SWITCH_STATE_ON = 'ON'
    SWITCH_STATE_OFF = 'OFF'
    SWITCH_STATE_UNKNOWN = 'UNKNOWN'

    def __init__(self,
                 host: str,
                 protocol: 'TPLinkSmartHomeProtocol' = None) -> None:
        SmartDevice.__init__(self, host, protocol)
        self.emeter_type = "emeter"

    @property
    def state(self) -> str:
        """
        Retrieve the switch state

        :returns: one of
                  SWITCH_STATE_ON
                  SWITCH_STATE_OFF
                  SWITCH_STATE_UNKNOWN
        :rtype: str
        """
        relay_state = self.sys_info['relay_state']

        if relay_state == 0:
            return SmartStrip.SWITCH_STATE_OFF
        elif relay_state == 1:
            return SmartStrip.SWITCH_STATE_ON
        else:
            _LOGGER.warning("Unknown state %s returned.", relay_state)
            return SmartStrip.SWITCH_STATE_UNKNOWN

    @state.setter
    def state(self, value: str):
        """
        Set the new switch state

        :param value: one of
                    SWITCH_STATE_ON
                    SWITCH_STATE_OFF
        :raises ValueError: on invalid state
        :raises SmartDeviceException: on error

        """
        if not isinstance(value, str):
            raise ValueError("State must be str, not of %s.", type(value))
        elif value.upper() == SmartStrip.SWITCH_STATE_ON:
            self.turn_on()
        elif value.upper() == SmartStrip.SWITCH_STATE_OFF:
            self.turn_off()
        else:
            raise ValueError("State %s is not valid.", value)

    @property
    def brightness(self) -> Optional[int]:
        """
        Current brightness of the device, if supported.
        Will return a a range between 0 - 100.

        :returns: integer
        :rtype: int

        """
        if not self.is_dimmable:
            return None

        return int(self.sys_info['brightness'])

    @brightness.setter
    def brightness(self, value: int):
        """
        Set the new switch brightness level.

        Note:
        When setting brightness, if the light is not
        already on, it will be turned on automatically.

        :param value: integer between 1 and 100

        """
        if not self.is_dimmable:
            return None

        if not isinstance(value, int):
            raise ValueError("Brightness must be integer, "
                             "not of %s.", type(value))
        elif value > 0 and value <= 100:
            self.turn_on()
            self._query_helper("smartlife.iot.dimmer", "set_brightness",
                               {"brightness": value})
        else:
            raise ValueError("Brightness value %s is not valid.", value)

    @property
    def is_dimmable(self):
        """
        Whether the switch supports brightness changes

        :return: True if switch supports brightness changes, False otherwise
        :rtype: bool

        """
        dimmable = False
        if "brightness" in self.sys_info:
            dimmable = True
        return dimmable

    @property
    def has_emeter(self):
        """
        Returns whether device has an energy meter.
        :return: True if energy meter is available
                 False otherwise
        """
        features = self.sys_info['feature'].split(':')
        return SmartDevice.FEATURE_ENERGY_METER in features

    def is_on(self, index: int) -> bool:
        """
        Returns whether device is on.

        param index: plug index
        :return: True if device is on, False otherwise
        """
        return bool(self.sys_info['children'][index]['state'])

    def turn_on(self):
        """
        Turn all outlets on

        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_relay_state", {"state": 1})

    def turn_off(self):
        """
        Turn all outlets off

        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_relay_state", {"state": 0})

    def turn_on_plug(self, index: int):
        """
        Turns a single outlet on.

        param index: plug index
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_relay_state", {"state": 1},
                           self._index_to_id(index))

    def turn_off_plug(self, index: int):
        """
        Turns a single outlet off.

        :param index: plug index
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_relay_state", {"state": 0},
                           self._index_to_id(index))

    def _index_to_id(self, index: int) -> str:
        """
        Returns the child ID for the given plug index

        :param index: plug index (1 based, not zero based)
        :raises SmartDeviceException: on error
        :return: child ID string
        :rtype: datetime
        """
        return self.sys_info["children"][index-1]["id"]

    @property
    def led(self) -> bool:
        """
        Returns the state of the led.

        :return: True if led is on, False otherwise
        :rtype: bool
        """
        return bool(1 - self.sys_info["led_off"])

    @led.setter
    def led(self, state: bool):
        """
        Sets the state of the led (night mode)

        :param bool state: True to set led on, False to set led off
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_led_off", {"off": int(not state)})

    def on_since(self, index: int) -> datetime.datetime:
        """
        Returns pretty-printed on-time

        :param index: index index
        :return: datetime for on since
        :rtype: datetime
        """
        return datetime.datetime.now() - \
            datetime.timedelta(seconds= \
            self.sys_info["children"][index]["on_time"])

    @property
    def state_information(self) -> Dict[str, Any]:
        state = {'LED state': self.led}
        for index in range(0, self.num_plugs):
            state['Plug %d on since' % (index + 1)] = self.on_since(index)
        return state

    @property
    def num_plugs(self) -> int:
        """
        Returns the number of plugs

        :rtype: int
        """
        return self.sys_info["child_num"]

    def get_emeter_realtime(self, index: int = None) -> Optional[Dict]:
        """
        Retrive current energy readings from device.

        :returns: current readings or False
        :rtype: dict, None
                  None if device has no energy meter or error occured
        :raises SmartDeviceException: on error
        """
        if not self.has_emeter:
            return None
        if index is None:
            child_id = None
        else:
            child_id = self._index_to_id(index)
        return super().get_emeter_realtime(child_id)

