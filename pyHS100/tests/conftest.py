import pytest
import glob
import json
import os
from .fakes import FakeTransportProtocol
from os.path import basename
from pyHS100 import SmartPlug, SmartBulb, Discover

SUPPORTED_DEVICES = glob.glob(os.path.dirname(os.path.abspath(__file__)) + "/fixtures/*.json")
# TODO add HS300 tests
SUPPORTED_DEVICES = [dev for dev in SUPPORTED_DEVICES if 'HS300' not in dev]


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
        if 'LB' in model:
            p = SmartBulb("123.123.123.123", protocol=FakeTransportProtocol(sysinfo))
        #elif 'HS300' in model:
        #    p = SmartStrip("123.123.123.123", protocol=FakeTransportProtocol(sysinfo))
        elif 'HS' in model:
            p = SmartPlug("123.123.123.123", protocol=FakeTransportProtocol(sysinfo))
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



#@pytest.yield_fixture(scope='session')
#def pg_server(pg_tag):


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--ip"):
        print("Testing against fixtures.")
        return
    else:
        print("Running against ip %s" % config.getoption("--ip"))