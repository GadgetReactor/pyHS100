import datetime
import logging
from typing import Any, Dict, Optional

from pyHS100 import SmartPlug

_LOGGER = logging.getLogger(__name__)


class SmartStrip(SmartPlug):
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
        SmartPlug.__init__(self, host, protocol)
        self.emeter_type = "emeter"
        self.plug = []
        for plug in self.sys_info["children"]:
            self.plug.append(SmartPlug(host, protocol, context=plug["id"]))

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

    def is_on(self, index: int) -> bool:
        """
        Returns whether device is on.

        :param index: plug index
        :return: True if device is on, False otherwise
        """
        return self.plug[index].is_on()

    def turn_on(self, index: int):
        """
        Turns an outlet on

        :param index: plug index
        :raises SmartDeviceException: on error
        """
        self.plug[index].turn_on()

    def turn_off(self, index: int):
        """
        Turns an outlet off

        :param index: plug index
        :raises SmartDeviceException: on error
        """
        self.plug[index].turn_off()

    def on_since(self, index: int) -> datetime.datetime:
        """
        Returns pretty-printed on-time

        :param index: plug index
        :return: datetime for on since
        :rtype: datetime
        """
        return self.plug[index].on_since

    @property
    def state_information(self) -> Dict[str, Any]:
        """
        Returns strip-specific state information.

        :return: Strip information dict, keys in user-presentable form.
        :rtype: dict
        """
        state = {'LED state': self.led}
        for plug_index in range(self.sys_info["child_num"]):
            state['Plug %d on since' % (plug_index + 1)] = \
                self.on_since(plug_index)
        return state

    def get_emeter_realtime(self) -> Optional[list]:
        """
        Retrieve current energy readings from device

        :returns: list of current readings or False
        :rtype: List, None
                  None if device has no energy meter or error occurred
        :raises SmartDeviceException: on error
        """
        if not self.has_emeter:
            return None

        emeter_status = []
        for index in range(self.num_children):
            emeter_status.append(self.plug[index].get_emeter_realtime())
        return emeter_status
