import datetime

from unittest.mock import patch

import pytest
from os.path import basename

from pyHS100 import DeviceType
from .newfakes import *
from .conftest import SUPPORTED_DEVICES


BULBS = {'LB100', 'LB120', 'LB130'}
VARIABLE_TEMP = {'LB120', 'LB130'}
PLUGS = {'HS100', 'HS105', 'HS110', 'HS200', 'HS220'}
COLOR_BULBS = {'LB130'}
DIMMABLE = {*BULBS, 'HS220'}
EMETER = {'HS110', 'HS300', *BULBS}

ALL_DEVICES = BULBS.union(PLUGS)


def filter_model(filter):
    print(filter)
    filtered = list()
    for dev in SUPPORTED_DEVICES:
        for filt in filter:
            if filt in basename(dev):
                filtered.append(dev)

    return filtered


has_emeter = pytest.mark.parametrize('dev', filter_model(EMETER), indirect=True)
no_emeter = pytest.mark.parametrize('dev', filter_model(ALL_DEVICES - EMETER), indirect=True)

bulb = pytest.mark.parametrize('dev', filter_model(BULBS), indirect=True)
plug = pytest.mark.parametrize('dev', filter_model(PLUGS), indirect=True)

dimmable = pytest.mark.parametrize('dev', filter_model(DIMMABLE), indirect=True)
non_dimmable = pytest.mark.parametrize('dev', filter_model(ALL_DEVICES - DIMMABLE), indirect=True)

variable_temp = pytest.mark.parametrize('dev', filter_model(VARIABLE_TEMP), indirect=True)
non_variable_temp = pytest.mark.parametrize('dev', filter_model(BULBS - VARIABLE_TEMP), indirect=True)

color_bulb = pytest.mark.parametrize('dev', filter_model(COLOR_BULBS), indirect=True)
non_color_bulb = pytest.mark.parametrize('dev', filter_model(BULBS - COLOR_BULBS), indirect=True)

# Parametrize tests to run with device both on and off
turn_on = pytest.mark.parametrize("turn_on", [True, False])


def handle_turn_on(dev, turn_on):
    if turn_on:
        dev.turn_on()
    else:
        dev.turn_off()


@plug
def test_plug_sysinfo(dev):
    assert dev.sys_info is not None
    PLUG_SCHEMA(dev.sys_info)

    assert dev.model is not None

    assert dev.device_type == DeviceType.Plug
    assert dev.is_plug


@bulb
def test_bulb_sysinfo(dev):
    assert dev.sys_info is not None
    BULB_SCHEMA(dev.sys_info)

    assert dev.model is not None

    assert dev.device_type == DeviceType.Bulb
    assert dev.is_bulb


def test_state_info(dev):
    assert isinstance(dev.state_information, dict)


def test_invalid_connection(dev):
    with patch.object(FakeTransportProtocol, 'query', side_effect=SmartDeviceException):
        with pytest.raises(SmartDeviceException):
            assert dev.is_on


def test_query_helper(dev):
    with pytest.raises(SmartDeviceException):
        dev._query_helper("test", "testcmd", {})
    # TODO check for unwrapping?


def test_deprecated_state(dev):
    with pytest.deprecated_call():
        dev.state = "OFF"
        assert dev.state == "OFF"
        assert not dev.is_on

    with pytest.deprecated_call():
        dev.state = "ON"
        assert dev.state == "ON"
        assert dev.is_on

    with pytest.deprecated_call():
        with pytest.raises(ValueError):
            dev.state = "foo"

    with pytest.deprecated_call():
        with pytest.raises(ValueError):
            dev.state = 1234


def test_deprecated_alias(dev):
    with pytest.deprecated_call():
        dev.alias = "foo"

def test_deprecated_mac(dev):
    with pytest.deprecated_call():
        dev.mac = 123123123123


@plug
def test_deprecated_led(dev):
    with pytest.deprecated_call():
        dev.led = True


@turn_on
def test_state(dev, turn_on):
    handle_turn_on(dev, turn_on)
    orig_state = dev.is_on
    if orig_state:
        dev.turn_off()
        assert not dev.is_on
        assert dev.is_off
        dev.turn_on()
        assert dev.is_on
        assert not dev.is_off
    else:
        dev.turn_on()
        assert dev.is_on
        assert not dev.is_off
        dev.turn_off()
        assert not dev.is_on
        assert dev.is_off


@no_emeter
def test_no_emeter(dev):
    assert not dev.has_emeter

    with pytest.raises(SmartDeviceException):
        dev.get_emeter_realtime()
    with pytest.raises(SmartDeviceException):
        dev.get_emeter_daily()
    with pytest.raises(SmartDeviceException):
        dev.get_emeter_monthly()
    with pytest.raises(SmartDeviceException):
        dev.erase_emeter_stats()


@has_emeter
def test_get_emeter_realtime(dev):
    assert dev.has_emeter

    current_emeter = dev.get_emeter_realtime()
    CURRENT_CONSUMPTION_SCHEMA(current_emeter)


@has_emeter
def test_get_emeter_daily(dev):
    assert dev.has_emeter

    assert dev.get_emeter_daily(year=1900, month=1) == {}

    d = dev.get_emeter_daily()
    assert len(d) > 0

    k, v = d.popitem()
    assert isinstance(k, int)
    assert isinstance(v, float)

    # Test kwh (energy, energy_wh)
    d = dev.get_emeter_daily(kwh=False)
    k2, v2 = d.popitem()
    assert v * 1000 == v2


@has_emeter
def test_get_emeter_monthly(dev):
    assert dev.has_emeter

    assert dev.get_emeter_monthly(year=1900) == {}

    d = dev.get_emeter_monthly()
    assert len(d) > 0

    k, v = d.popitem()
    assert isinstance(k, int)
    assert isinstance(v, float)

    # Test kwh (energy, energy_wh)
    d = dev.get_emeter_monthly(kwh=False)
    k2, v2 = d.popitem()
    assert v * 1000 == v2


@has_emeter
def test_emeter_status(dev):
    assert dev.has_emeter

    d = dev.get_emeter_realtime()

    with pytest.raises(KeyError):
        assert d["foo"]

    assert d["power_mw"] == d["power"] * 1000
    # bulbs have only power according to tplink simulator.
    if not dev.is_bulb:
        assert d["voltage_mv"] == d["voltage"] * 1000

        assert d["current_ma"] == d["current"] * 1000
        assert d["total_wh"] == d["total"] * 1000


@pytest.mark.skip("not clearing your stats..")
@has_emeter
def test_erase_emeter_stats(dev):
    assert dev.has_emeter

    dev.erase_emeter()


@has_emeter
def test_current_consumption(dev):
    if dev.has_emeter:
        x = dev.current_consumption()
        assert isinstance(x, float)
        assert x >= 0.0
    else:
        assert dev.current_consumption() is None


def test_alias(dev):
    test_alias = "TEST1234"
    original = dev.alias
    assert isinstance(original, str)

    dev.set_alias(test_alias)
    assert dev.alias == test_alias

    dev.set_alias(original)
    assert dev.alias == original


@plug
def test_led(dev):
    original = dev.led

    dev.set_led(False)
    assert not dev.led
    dev.set_led(True)

    assert dev.led

    dev.set_led(original)


@plug
def test_on_since(dev):
    assert isinstance(dev.on_since, datetime.datetime)


def test_icon(dev):
    assert set(dev.icon.keys()), {'icon', 'hash'}


def test_time(dev):
    assert isinstance(dev.time, datetime.datetime)
    # TODO check setting?


def test_timezone(dev):
    TZ_SCHEMA(dev.timezone)


def test_hw_info(dev):
    PLUG_SCHEMA(dev.hw_info)


def test_location(dev):
    PLUG_SCHEMA(dev.location)


def test_rssi(dev):
    PLUG_SCHEMA({'rssi': dev.rssi})  # wrapping for vol


def test_mac(dev):
    PLUG_SCHEMA({'mac': dev.mac})  # wrapping for val
    # TODO check setting?


@non_variable_temp
def test_temperature_on_nonsupporting(dev):
    assert dev.valid_temperature_range == (0, 0)

    # TODO test when device does not support temperature range
    with pytest.raises(SmartDeviceException):
        dev.set_color_temp(2700)
    with pytest.raises(SmartDeviceException):
        print(dev.color_temp)


@variable_temp
def test_out_of_range_temperature(dev):
    with pytest.raises(ValueError):
        dev.set_color_temp(1000)
    with pytest.raises(ValueError):
        dev.set_color_temp(10000)


@non_dimmable
def test_non_dimmable(dev):
    assert not dev.is_dimmable

    with pytest.raises(SmartDeviceException):
        assert dev.brightness == 0
    with pytest.raises(SmartDeviceException):
        dev.set_brightness(100)


@dimmable
@turn_on
def test_dimmable_brightness(dev, turn_on):
    handle_turn_on(dev, turn_on)
    assert dev.is_dimmable

    dev.set_brightness(50)
    assert dev.brightness == 50

    dev.set_brightness(10)
    assert dev.brightness == 10

    with pytest.raises(SmartDeviceException):
        dev.set_brightness("foo")


@dimmable
def test_invalid_brightness(dev):
    assert dev.is_dimmable

    with pytest.raises(SmartDeviceException):
        dev.set_brightness(110)

    with pytest.raises(SmartDeviceException):
        dev.set_brightness(-100)


@color_bulb
@turn_on
def test_hsv(dev, turn_on):
    handle_turn_on(dev, turn_on)
    assert dev.is_color

    hue, saturation, brightness = dev.hsv
    assert 0 <= hue <= 255
    assert 0 <= saturation <= 100
    assert 0 <= brightness <= 100

    dev.set_hsv(hue=1, saturation=1, value=1)

    hue, saturation, brightness = dev.hsv
    assert hue == 1
    assert saturation == 1
    assert brightness == 1


@color_bulb
@turn_on
def test_invalid_hsv(dev, turn_on):
    handle_turn_on(dev, turn_on)

    assert dev.is_color

    for invalid_hue in [-1, 256, 0.5]:
        with pytest.raises(SmartDeviceException):
            dev.set_hsv(invalid_hue, 0, 0)

    for invalid_saturation in [-1, 101, 0.5]:
        with pytest.raises(SmartDeviceException):
            dev.set_hsv(0, invalid_saturation, 0)

    for invalid_brightness in [-1, 101, 0.5]:
        with pytest.raises(SmartDeviceException):
            dev.set_hsv(0, 0, invalid_brightness)


@non_color_bulb
def test_hsv_on_non_color(dev):
    assert not dev.is_color

    with pytest.raises(SmartDeviceException):
        dev.set_hsv(0, 0, 0)
    with pytest.raises(SmartDeviceException):
        print(dev.hsv)


@variable_temp
@turn_on
def test_try_set_colortemp(dev, turn_on):
    handle_turn_on(dev, turn_on)

    dev.set_color_temp(2700)
    assert dev.color_temp == 2700


@variable_temp
@turn_on
def test_deprecated_colortemp(dev, turn_on):
    handle_turn_on(dev, turn_on)
    with pytest.deprecated_call():
        dev.color_temp = 2700


@dimmable
def test_deprecated_brightness(dev):
    with pytest.deprecated_call():
        dev.brightness = 10


@non_variable_temp
def test_non_variable_temp(dev):
    with pytest.raises(SmartDeviceException):
        dev.set_color_temp(2700)


@color_bulb
@turn_on
def test_deprecated_hsv(dev, turn_on):
    handle_turn_on(dev, turn_on)
    with pytest.deprecated_call():
        dev.hsv = (1, 1, 1)
