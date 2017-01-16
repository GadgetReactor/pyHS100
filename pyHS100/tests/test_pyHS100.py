from __future__ import absolute_import
from __future__ import unicode_literals

from unittest import TestCase, skip, skipIf
from voluptuous import Schema, Invalid, All, Range
from functools import partial
import datetime
import re

from pyHS100 import SmartPlug, SmartPlugException
from pyHS100.tests.fakes import FakeTransportProtocol, sysinfo_hs110

PLUG_IP = '192.168.250.186'
SKIP_STATE_TESTS = False

# python2 compatibility
try:
    basestring
except NameError:
    basestring = str


def check_int_bool(x):
    if x != 0 and x != 1:
        raise Invalid(x)
    return x


def check_mac(x):
    if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", x.lower()):
        return x
    raise Invalid(x)


def check_mode(x):
    if x in ['schedule']:
        return x

    raise Invalid("invalid mode {}".format(x))


class TestSmartPlug(TestCase):
    # these schemas should go to the mainlib as
    # they can be useful when adding support for new features/devices
    # as well as to check that faked devices are operating properly.
    sysinfo_schema = Schema({
        'active_mode': check_mode,
        'alias': basestring,
        'dev_name': basestring,
        'deviceId': basestring,
        'feature': basestring,
        'fwId': basestring,
        'hwId': basestring,
        'hw_ver': basestring,
        'icon_hash': basestring,
        'latitude': All(float, Range(min=-90, max=90)),
        'led_off': check_int_bool,
        'longitude': All(float, Range(min=-180, max=180)),
        'mac': check_mac,
        'model': basestring,
        'oemId': basestring,
        'on_time': int,
        'relay_state': int,
        'rssi': All(int, Range(max=0)),
        'sw_ver': basestring,
        'type': basestring,
        'updating': check_int_bool,
    })

    current_consumption_schema = Schema({
        'voltage': All(float, Range(min=0, max=300)),
        'power': All(float, Range(min=0)),
        'total': All(float, Range(min=0)),
        'current': All(float, Range(min=0)),
    })

    tz_schema = Schema({
        'zone_str': basestring,
        'dst_offset': int,
        'index': All(int, Range(min=0)),
        'tz_str': basestring,
    })

    def setUp(self):
        self.plug = SmartPlug(PLUG_IP,
                              protocol=FakeTransportProtocol(sysinfo_hs110))

    def tearDown(self):
        self.plug = None

    def test_initialize(self):
        self.assertIsNotNone(self.plug.sys_info)
        self.sysinfo_schema(self.plug.sys_info)

    def test_initialize_invalid_connection(self):
        plug = SmartPlug('127.0.0.1',
                         protocol=FakeTransportProtocol(sysinfo_hs110,
                                                        invalid=True))
        with self.assertRaises(SmartPlugException):
            plug.sys_info['model']

    def test_query_helper(self):
        with self.assertRaises(SmartPlugException):
            self.plug._query_helper("test", "testcmd", {})
        # TODO check for unwrapping?

    @skipIf(SKIP_STATE_TESTS, "SKIP_STATE_TESTS is True, skipping")
    def test_state(self):
        def set_invalid(x):
            self.plug.state = x

        set_invalid_int = partial(set_invalid, 1234)
        self.assertRaises(ValueError, set_invalid_int)

        set_invalid_str = partial(set_invalid, "1234")
        self.assertRaises(ValueError, set_invalid_str)

        set_invalid_bool = partial(set_invalid, True)
        self.assertRaises(ValueError, set_invalid_bool)

        orig_state = self.plug.state
        if orig_state == SmartPlug.SWITCH_STATE_OFF:
            self.plug.state = "ON"
            self.assertTrue(self.plug.state == SmartPlug.SWITCH_STATE_ON)
            self.plug.state = "OFF"
            self.assertTrue(self.plug.state == SmartPlug.SWITCH_STATE_OFF)
        elif orig_state == SmartPlug.SWITCH_STATE_ON:
            self.plug.state = "OFF"
            self.assertTrue(self.plug.state == SmartPlug.SWITCH_STATE_OFF)
            self.plug.state = "ON"
            self.assertTrue(self.plug.state == SmartPlug.SWITCH_STATE_ON)
        elif orig_state == SmartPlug.SWITCH_STATE_UNKNOWN:
            self.fail("can't test for unknown state")

    def test_get_sysinfo(self):
        # initialize checks for this already, but just to be sure
        self.sysinfo_schema(self.plug.get_sysinfo())

    @skipIf(SKIP_STATE_TESTS, "SKIP_STATE_TESTS is True, skipping")
    def test_turns_and_isses(self):
        orig_state = self.plug.is_on

        if orig_state:
            self.plug.turn_off()
            self.assertFalse(self.plug.is_on)
            self.assertTrue(self.plug.is_off)
            self.plug.turn_on()
            self.assertTrue(self.plug.is_on)
        else:
            self.plug.turn_on()
            self.assertFalse(self.plug.is_off)
            self.assertTrue(self.plug.is_on)
            self.plug.turn_off()
            self.assertTrue(self.plug.is_off)

    def test_has_emeter(self):
        # a not so nice way for checking for emeter availability..
        if "110" in self.plug.sys_info["model"]:
            self.assertTrue(self.plug.has_emeter)
        else:
            self.assertFalse(self.plug.has_emeter)

    def test_get_emeter_realtime(self):
        self.current_consumption_schema((self.plug.get_emeter_realtime()))

    def test_get_emeter_daily(self):
        self.assertEqual(self.plug.get_emeter_daily(year=1900, month=1), {})

        k, v = self.plug.get_emeter_daily().popitem()
        self.assertTrue(isinstance(k, int))
        self.assertTrue(isinstance(v, float))

    def test_get_emeter_monthly(self):
        self.assertEqual(self.plug.get_emeter_monthly(year=1900), {})

        d = self.plug.get_emeter_monthly()
        k, v = d.popitem()
        self.assertTrue(isinstance(k, int))
        self.assertTrue(isinstance(v, float))

    @skip("not clearing your stats..")
    def test_erase_emeter_stats(self):
        self.fail()

    def test_current_consumption(self):
        x = self.plug.current_consumption()
        self.assertTrue(isinstance(x, float))
        self.assertTrue(x >= 0.0)

    def test_identify(self):
        ident = self.plug.identify()
        self.assertTrue(isinstance(ident, tuple))
        self.assertTrue(len(ident) == 3)

    def test_alias(self):
        test_alias = "TEST1234"
        original = self.plug.alias
        self.assertTrue(isinstance(original, basestring))
        self.plug.alias = test_alias
        self.assertEqual(self.plug.alias, test_alias)
        self.plug.alias = original
        self.assertEqual(self.plug.alias, original)

    def test_led(self):
        original = self.plug.led

        self.plug.led = False
        self.assertFalse(self.plug.led)
        self.plug.led = True
        self.assertTrue(self.plug.led)

        self.plug.led = original

    def test_icon(self):
        self.assertEqual(set(self.plug.icon.keys()), {'icon', 'hash'})

    def test_time(self):
        self.assertTrue(isinstance(self.plug.time, datetime.datetime))
        # TODO check setting?

    def test_timezone(self):
        self.tz_schema(self.plug.timezone)

    def test_hw_info(self):
        self.sysinfo_schema(self.plug.hw_info)

    def test_on_since(self):
        self.assertTrue(isinstance(self.plug.on_since, datetime.datetime))

    def test_location(self):
        self.sysinfo_schema(self.plug.location)

    def test_rssi(self):
        self.sysinfo_schema({'rssi': self.plug.rssi})  # wrapping for vol

    def test_mac(self):
        self.sysinfo_schema({'mac': self.plug.mac})  # wrapping for val
        # TODO check setting?
