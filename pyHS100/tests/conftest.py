import pytest
import glob
import json
import os
from .newfakes import FakeTransportProtocol
from os.path import basename
from pyHS100 import SmartPlug, SmartBulb, SmartStrip, Discover

SUPPORTED_DEVICES = glob.glob(
    os.path.dirname(os.path.abspath(__file__)) + "/fixtures/*.json"
)
# TODO add HS300 tests
# SUPPORTED_DEVICES = [dev for dev in SUPPORTED_DEVICES if 'HS300' not in dev]

BULBS = {"LB100", "LB120", "LB130"}
VARIABLE_TEMP = {"LB120", "LB130"}
PLUGS = {"HS100", "HS105", "HS110", "HS200", "HS220", "HS300"}
STRIPS = {"HS300"}
COLOR_BULBS = {"LB130"}
DIMMABLE = {*BULBS, "HS220"}
EMETER = {"HS110", "HS300", *BULBS}

ALL_DEVICES = BULBS.union(PLUGS)


def filter_model(filter):
    print(filter)
    filtered = list()
    for dev in SUPPORTED_DEVICES:
        for filt in filter:
            if filt in basename(dev):
                filtered.append(dev)

    return filtered


has_emeter = pytest.mark.parametrize(
    "dev", filter_model(EMETER), indirect=True
)
no_emeter = pytest.mark.parametrize(
    "dev", filter_model(ALL_DEVICES - EMETER), indirect=True
)

bulb = pytest.mark.parametrize("dev", filter_model(BULBS), indirect=True)
plug = pytest.mark.parametrize("dev", filter_model(PLUGS), indirect=True)
strip = pytest.mark.parametrize("dev", filter_model(STRIPS), indirect=True)

dimmable = pytest.mark.parametrize(
    "dev", filter_model(DIMMABLE), indirect=True
)
non_dimmable = pytest.mark.parametrize(
    "dev", filter_model(ALL_DEVICES - DIMMABLE), indirect=True
)

variable_temp = pytest.mark.parametrize(
    "dev", filter_model(VARIABLE_TEMP), indirect=True
)
non_variable_temp = pytest.mark.parametrize(
    "dev", filter_model(BULBS - VARIABLE_TEMP), indirect=True
)

color_bulb = pytest.mark.parametrize(
    "dev", filter_model(COLOR_BULBS), indirect=True
)
non_color_bulb = pytest.mark.parametrize(
    "dev", filter_model(BULBS - COLOR_BULBS), indirect=True
)


# Parametrize tests to run with device both on and off
turn_on = pytest.mark.parametrize("turn_on", [True, False])


def handle_turn_on(dev, turn_on):
    if turn_on:
        dev.turn_on()
    else:
        dev.turn_off()


@pytest.fixture(params=SUPPORTED_DEVICES)
def dev(request):
    file = request.param

    ip = request.config.getoption("--ip")
    if ip:
        d = Discover.discover_single(ip)
        print(d.model)
        if d.model in file:
            return d
        return

    with open(file) as f:
        sysinfo = json.load(f)
        model = basename(file)
        if "LB" in model:
            p = SmartBulb(
                "123.123.123.123", protocol=FakeTransportProtocol(sysinfo)
            )
        elif "HS300" in model:
            p = SmartStrip(
                "123.123.123.123", protocol=FakeTransportProtocol(sysinfo)
            )
        elif "HS" in model:
            p = SmartPlug(
                "123.123.123.123", protocol=FakeTransportProtocol(sysinfo)
            )
        else:
            raise Exception("No tests for %s" % model)
        yield p


def pytest_addoption(parser):
    parser.addoption(
        "--ip", action="store", default=None, help="run against device"
    )


"""
def pytest_generate_tests(metafunc):
    if 'dev' in metafunc.fixturenames:
        ip = metafunc.config.getoption("ip")
        print("ip: %s" % ip)
        if ip:
            devs = ip
        else:
            devs = SUPPORTED_DEVICES
        print("parametrizing dev with %s" % devs)
        metafunc.parametrize("dev", devs)
"""


# @pytest.yield_fixture(scope='session')
# def pg_server(pg_tag):


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--ip"):
        print("Testing against fixtures.")
        return
    else:
        print("Running against ip %s" % config.getoption("--ip"))
