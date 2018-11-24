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

    def __init__(self,
                 host: str,
                 protocol: 'TPLinkSmartHomeProtocol' = None) -> None:
        SmartPlug.__init__(self, host, protocol)
        self.emeter_type = "emeter"
        self.plugs = []
        for plug in self.sys_info["children"]:
            self.plugs.append(SmartPlug(host, protocol, context=plug["id"]))

    @property
    def state(self) -> Dict[int, str]:
        """
        Retrieve the switch state

        :returns: list with the state of each child plug
                  SWITCH_STATE_ON
                  SWITCH_STATE_OFF
                  SWITCH_STATE_UNKNOWN
        :rtype: dict
        """
        states = {}
        for plug in range(self.num_children):
            relay_state = self.sys_info["children"][plug]["state"]

            if relay_state == 0:
                switch_state = SmartPlug.SWITCH_STATE_OFF
            if relay_state == 1:
                switch_state = SmartPlug.SWITCH_STATE_ON
            else:
                _LOGGER.warning("Unknown state %s returned.", relay_state)
                switch_state = SmartPlug.SWITCH_STATE_UNKNOWN

            states[plug] = switch_state

        return states

    @state.setter
    def state(self, value: str):
        """
        Sets the state of all plugs in the strip

        :param value: one of
                    SWITCH_STATE_ON
                    SWITCH_STATE_OFF
        :raises ValueError: on invalid state
        :raises SmartDeviceException: on error

        """
        if not isinstance(value, str):
            raise ValueError("State must be str, not of %s.", type(value))
        elif value.upper() == SmartPlug.SWITCH_STATE_ON:
            self.turn_on()
        elif value.upper() == SmartPlug.SWITCH_STATE_OFF:
            self.turn_off()
        else:
            raise ValueError("State %s is not valid.", value)

    def set_state(self, value: str, *, index: int = -1):
        """
        sets the state of a plug on the strip

        :param value: one of
                    SWITCH_STATE_ON
                    SWITCH_STATE_OFF
        :param index: plug index (-1 for all)
        :raises ValueError: on invalid state
        :raises SmartDeviceException: on error
        """
        self.plugs[index].set_state(value)

    def is_on(self, *, index: int = -1) -> Any:
        """
        Returns whether device is on.

        :param index: plug index (-1 for all)
        :return: True if device is on, False otherwise, Dict without index
        """
        if index < 0:
            is_on = {}
            for plug in range(self.num_children):
                is_on[plug] = self.plug[plug].is_on()
            return is_on
        else:
            return self.plugs[index].is_on()

    def turn_on(self, *, index: int = -1):
        """
        Turns outlets on

        :param index: plug index (-1 for all)
        :raises SmartDeviceException: on error
        """
        if index < 0:
            self._query_helper("system", "set_relay_state", {"state": 1})
        else:
            self.plugs[index].turn_on()

    def turn_off(self, *, index: int = -1):
        """
        Turns outlets off

        :param index: plug index (-1 for all)
        :raises SmartDeviceException: on error
        """
        if index < 0:
            self._query_helper("system", "set_relay_state", {"state": 0})
        else:
            self.plugs[index].turn_off()

    def on_since(self, *, index: int = -1) -> Any:
        """
        Returns pretty-printed on-time

        :param index: plug index (-1 for all)
        :return: datetime for on since
        :rtype: datetime with index, Dict[int, str] without index
        """
        if index < 0:
            on_since = {}
            for plug in range(self.num_children):
                on_since[plug] = self.plugs[plug].on_since
            return on_since
        else:
            return self.plugs[index].on_since

    @property
    def state_information(self) -> Dict[str, Any]:
        """
        Returns strip-specific state information.

        :return: Strip information dict, keys in user-presentable form.
        :rtype: dict
        """
        state = {'LED state': self.led}
        for plug_index in range(self.num_children):
            state['Plug %d on since' % (plug_index + 1)] = \
                self.on_since(index=plug_index)
        return state

    def get_emeter_realtime(self, *,
                            index: int = -1) -> Any:
        """
        Retrieve current energy readings from device

        :param index: plug index (-1 for all)
        :returns: list of current readings or False
        :rtype: Dict, Dict[int, Dict], None
                Dict if index is provided
                Dict[int, Dict] if no index provided
                None if device has no energy meter or error occurred
        :raises SmartDeviceException: on error
        """
        if not self.has_emeter:
            return None

        if index < 0:
            emeter_status = {}
            for plug in range(self.num_children):
                emeter_status[plug] = self.plugs[plug].get_emeter_realtime()
            return emeter_status
        else:
            return self.plugs[index].get_emeter_realtime()
