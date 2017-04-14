import sys
import click
import logging
from click_datetime import Datetime
from pprint import pformat

if sys.version_info < (3, 4):
    print("To use this script you need python 3.4 or newer! got %s" %
          sys.version_info)
    sys.exit(1)

from pyHS100 import (SmartDevice, SmartPlug, SmartBulb,
                     TPLinkSmartHomeProtocol)  # noqa: E402

pass_dev = click.make_pass_decorator(SmartDevice)


@click.group(invoke_without_command=True)
@click.option('--ip', envvar="PYHS100_IP", required=False)
@click.option('--debug/--normal', default=False)
@click.option('--bulb', default=False, is_flag=True)
@click.pass_context
def cli(ctx, ip, debug, bulb):
    """A cli tool for controlling TP-Link smart home plugs."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if ctx.invoked_subcommand == "discover":
        return

    if ip is None:
        click.echo("You must specify the IP!")
        sys.exit(-1)

    if bulb:
        dev = SmartBulb(ip)
    else:
        dev = SmartPlug(ip)
    ctx.obj = dev

    if ctx.invoked_subcommand is None:
        ctx.invoke(state)


@cli.command()
@click.option('--timeout', default=5, required=False)
def discover(timeout):
    """Discover devices in the network."""
    click.echo("Discovering devices for %s seconds" % timeout)
    for dev in TPLinkSmartHomeProtocol.discover(timeout=timeout):
        print("Found device: %s" % pformat(dev))


@cli.command()
@pass_dev
def sysinfo(dev):
    """Print out full system information."""
    click.echo(click.style("== System info ==", bold=True))
    click.echo(pformat(dev.sys_info))


@cli.command()
@pass_dev
@click.pass_context
def state(ctx, dev):
    """Print out device state and versions."""
    click.echo(click.style("== %s - %s ==" % (dev.alias, dev.model),
                           bold=True))

    click.echo(click.style("Device state: %s" % "ON" if dev.is_on else "OFF",
                           fg="green" if dev.is_on else "red"))
    for k, v in dev.state_information.items():
        click.echo("%s: %s" % (k, v))
    click.echo(click.style("== Generic information ==", bold=True))
    click.echo("Time:         %s" % dev.time)
    click.echo("Hardware:     %s" % dev.hw_info["hw_ver"])
    click.echo("Software:     %s" % dev.hw_info["sw_ver"])
    click.echo("MAC (rssi):   %s (%s)" % (dev.mac, dev.rssi))
    click.echo("Location:     %s" % dev.location)

    ctx.invoke(emeter)


@cli.command()
@pass_dev
@click.option('--year', type=Datetime(format='%Y'),
              default=None, required=False)
@click.option('--month', type=Datetime(format='%Y-%m'),
              default=None, required=False)
@click.option('--erase', is_flag=True)
def emeter(dev, year, month, erase):
    """Query emeter for historical consumption."""
    click.echo(click.style("== Emeter ==", bold=True))
    if not dev.has_emeter:
        click.echo("Device has no emeter")
        return

    if erase:
        click.echo("Erasing emeter statistics..")
        dev.erase_emeter_stats()
        return

    click.echo("Current state: %s" % dev.get_emeter_realtime())
    if year:
        click.echo("== For year %s ==" % year.year)
        click.echo(dev.get_emeter_monthly(year.year))
    elif month:
        click.echo("== For month %s of %s ==" % (month.month, month.year))
        dev.get_emeter_daily(year=month.year, month=month.month)


@cli.command()
@click.argument("brightness", type=click.IntRange(0, 100), default=None)
@pass_dev
def brightness(dev, value):
    """Get or set brightness. (Bulb Only)"""
    if value is None:
        click.echo("Brightness: %s" % dev.brightness)
    else:
        click.echo("Setting brightness to %s" % value)
        dev.brightness = value


@cli.command()
@click.argument("temperature", type=click.IntRange(2700, 6500), default=None)
@pass_dev
def temperature(dev, value):
    """Get or set color temperature. (Bulb only)"""
    if value is None:
        click.echo("Color temperature: %s" % dev.color_temp)
    else:
        click.echo("Setting color temperature to %s" % value)
        dev.color_temp = value


@cli.command()
@click.argument("h", type=click.IntRange(0, 255), default=None)
@click.argument("s", type=click.IntRange(0, 255), default=None)
@click.argument("v", type=click.IntRange(0, 255), default=None)
def hsv(dev, h, s, v):
    """Get or set color in HSV. (Bulb only)"""
    if h is None or s is None or v is None:
        click.echo("Current HSV: %s" % dev.hsv)
    else:
        click.echo("Setting HSV: %s %s %s" % (h, s, v))
        dev.hsv = (h, s, v)


@cli.command()
@click.argument('state', type=bool, required=False)
@pass_dev
def led(dev, state):
    """Get or set led state. (Plug only)"""
    if state is not None:
        click.echo("Turning led to %s" % state)
        dev.led = state
    else:
        click.echo("LED state: %s" % dev.led)


@cli.command()
@pass_dev
def on(plug):
    """Turn the device on."""
    click.echo("Turning on..")
    plug.turn_on()


@cli.command()
@pass_dev
def off(plug):
    """Turn the device off."""
    click.echo("Turning off..")
    plug.turn_off()


if __name__ == "__main__":
    cli()
