"""This module contains various helper classes that make handling targets and sets
of targets and results easier."""
import binascii
import collections
import ipaddress
import logging

from knxmap.data.constants import *
from knxmap.messages import KnxMessage
from knxmap.utils import make_runstate_printable

__all__ = [
    "Targets",
    "KnxTargets",
    "BusResultSet",
    "KnxTargetReport",
    "KnxBusTargetReport",
    "print_knx_target",
]

LOGGER = logging.getLogger(__name__)


class Targets:
    """A helper class that expands provided target definitions to a list of tuples."""

    def __init__(self, targets=None, ports=3671):
        self.targets = set()
        self.ports = set()
        if isinstance(ports, list):
            for p in ports:
                self.ports.add(p)
        elif isinstance(ports, int):
            self.ports.add(ports)
        else:
            self.ports.add(3671)

        if isinstance(targets, (set, list)):
            self._parse(targets)
        elif isinstance(targets, str):
            self._parse([targets])

    def _parse(self, targets):
        """Parse all targets with ipaddress module (with CIDR notation support)."""
        for target in targets:
            try:
                _targets = ipaddress.ip_network(target, strict=False)
            except ValueError:
                LOGGER.error(f"Invalid target definition, ignoring it: {target}")
                continue

            if "/" in target:
                _targets = _targets.hosts()

            for _target in _targets:
                for port in self.ports:
                    self.targets.add((str(_target), port))


class KnxTargets:
    """A helper class that expands knx bus targets to lists."""

    def __init__(self, targets):
        self.targets = set()
        if not targets:
            self.targets = None
        elif "-" not in targets:
            if not self.is_valid_physical_address(targets):
                LOGGER.error("Invalid physical address")
            else:
                self.targets.add(targets)
        else:
            assert isinstance(targets, str)
            if "-" in targets and targets.count("-") < 2:
                # TODO: also parse dashes in octets
                try:
                    f, t = targets.split("-")
                except ValueError:
                    return
                if not self.is_valid_physical_address(f):
                    LOGGER.error("Invalid physical address From")
                if not self.is_valid_physical_address(t):
                    LOGGER.error("Invalid physical address To")
                    # TODO: make it group address aware
                elif self.physical_address_to_int(t) <= self.physical_address_to_int(f):
                    LOGGER.error("From should be smaller then To")
                else:
                    self.targets = self.expand_targets(f, t)

    @staticmethod
    def target_gen(f, t):
        f = KnxMessage.pack_knx_address(f)
        t = KnxMessage.pack_knx_address(t)
        for i in range(f, t + 1):
            yield KnxMessage.parse_knx_address(i)

    @staticmethod
    def expand_targets(f, t):
        f = KnxMessage.pack_knx_address(f)
        t = KnxMessage.pack_knx_address(t)
        return {KnxMessage.parse_knx_address(i) for i in range(f, t + 1)}

    @staticmethod
    def physical_address_to_int(address):
        parts = address.split(".")
        return (int(parts[0]) << 12) + (int(parts[1]) << 8) + (int(parts[2]))

    @staticmethod
    def int_to_physical_address(address):
        return f"{address >> 12 & 15}.{address >> 8 & 15}.{address & 255}"

    @staticmethod
    def is_valid_physical_address(address):
        assert isinstance(address, str)
        try:
            parts = [int(i) for i in address.split(".")]
        except ValueError:
            return False
        if len(parts) != 3:
            return False
        if parts[0] < 0 or parts[0] > 15:
            return False
        if parts[1] < 0 or parts[1] > 15:
            return False
        if parts[2] < 0 or parts[2] > 255:
            return False
        return parts[0] != 0 or parts[1] != 0 or parts[2] != 0

    @staticmethod
    def is_valid_group_address(address):
        """See <https://support.knx.org/hc/de/articles/115003188109-Gruppenadressen>."""
        assert isinstance(address, str)
        try:
            parts = [int(i) for i in address.split("/")]
        except ValueError:
            return False
        if len(parts) < 2 or len(parts) > 3:
            return False
        if len(parts) == 3:
            if parts[0] < 0 or parts[0] > 31:
                return False
            if parts[1] < 0 or parts[1] > 7:
                return False
            if parts[2] < 0 or parts[2] > 255:
                return False
            if parts[0] == 0 and parts[1] == 0 and parts[2] == 0:
                return False
        if len(parts) == 2:
            if parts[0] < 0 or parts[0] > 31:
                return False
            if parts[1] < 0 or parts[1] > 2047:
                return False
            if parts[0] == 0 and parts[1] == 0:
                return False
        return True


class BusResultSet:
    # TODO: implement

    def __init__(self):
        self.targets = collections.OrderedDict()

    def add(self, target):
        """Add a target to the result set, at the right position."""


class KnxTargetReport:
    def __init__(
        self,
        host,
        port,
        mac_address,
        knx_address,
        device_serial,
        friendly_name,
        device_status,
        knx_medium,
        project_install_identifier,
        supported_services,
        bus_devices,
        additional_individual_addresses=None,
        manufacturer=None,
    ):
        self.host = host
        self.port = port
        self.mac_address = mac_address
        self.knx_address = knx_address
        self.device_serial = device_serial
        self.friendly_name = friendly_name
        self.device_status = device_status
        self.knx_medium = knx_medium
        self.project_install_identifier = project_install_identifier
        self.supported_services = supported_services
        self.bus_devices = bus_devices
        self.additional_individual_addresses = additional_individual_addresses or []
        self.manufacturer = manufacturer

    def __str__(self):
        return self.host

    def __repr__(self):
        return self.host


class KnxBusTargetReport:
    def __init__(
        self,
        address,
        medium=None,
        type=None,
        version=None,
        device_serial=None,
        manufacturer=None,
        properties=None,
        device_state=None,
    ):
        self.address = address
        self.medium = medium
        self.type = type
        self.version = version
        self.device_serial = device_serial
        self.device_state = device_state
        self.manufacturer = manufacturer
        self.properties = properties

    def __str__(self):
        return self.address

    def __repr__(self):
        return self.address


def print_knx_target(knx_target):
    """Print a target of type KnxTargetReport in a well formatted way."""
    # TODO: make this better, and prettier.
    out = {}
    out[knx_target.host] = collections.OrderedDict()
    o = out[knx_target.host]
    o["Port"] = knx_target.port
    o["MAC Address"] = knx_target.mac_address
    o["KNX Bus Address"] = knx_target.knx_address
    if knx_target.additional_individual_addresses:
        o["Additional Bus Addresses"] = knx_target.additional_individual_addresses
    o["KNX Device Serial"] = knx_target.device_serial
    o["KNX Medium"] = KNX_MEDIUMS.get(knx_target.knx_medium)
    if knx_target.manufacturer:
        o["Manufacturer"] = knx_target.manufacturer
    o["Device Friendly Name"] = binascii.b2a_qp(
        knx_target.friendly_name.strip().replace(b"\x00", b"")
    ).decode()
    o["Device Status"] = make_runstate_printable(knx_target.device_status)
    o["Project Install Identifier"] = knx_target.project_install_identifier
    o["Supported Services"] = knx_target.supported_services
    if knx_target.bus_devices:
        o["Bus Devices"] = []
        # Sort the device list based on KNX addresses
        x = {}
        for i in knx_target.bus_devices:
            x[KnxMessage.pack_knx_address(str(i))] = i
        bus_devices = collections.OrderedDict(sorted(x.items()))
        for k, d in bus_devices.items():
            _d = {}
            _d[d.address] = collections.OrderedDict()
            if hasattr(d, "type") and not isinstance(d.type, (type(None), type(False))):
                _d[d.address]["Type"] = DEVICE_TYPES.get(d.type)
            if hasattr(d, "medium") and not isinstance(
                d.medium, (type(None), type(False))
            ):
                _d[d.address]["Medium"] = KNX_BUS_MEDIUMS.get(d.medium)
            if hasattr(d, "device_serial") and not isinstance(
                d.device_serial, (type(None), type(False))
            ):
                _d[d.address]["Device Serial"] = d.device_serial
            if hasattr(d, "device_state") and not isinstance(
                d.device_state, (type(None), type(False))
            ):
                _d[d.address]["Device State"] = make_runstate_printable(d.device_state)
            if hasattr(d, "manufacturer") and not isinstance(
                d.manufacturer, (type(None), type(False))
            ):
                _d[d.address]["Manufacturer"] = d.manufacturer
            if hasattr(d, "version") and not isinstance(
                d.version, (type(None), type(False))
            ):
                _d[d.address]["Version"] = d.version
            if (
                hasattr(d, "properties")
                and isinstance(d.properties, dict)
                and d.properties
            ):
                _d[d.address]["Properties"] = d.properties
            o["Bus Devices"].append(_d)

    def print_fmt(d, indent=0):
        for key, value in d.items():
            if indent == 0:
                print("   " * indent + str(key))
            elif isinstance(value, (dict, collections.OrderedDict)):
                if not len(value.keys()):
                    print("   " * indent + str(key))
                else:
                    print("   " * indent + str(key) + ": ")
            else:
                print("   " * indent + str(key) + ": ", end="", flush=True)

            if key == "Bus Devices":
                print()
                for i in value:
                    print_fmt(i, indent + 1)
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    if i == 0:
                        print()
                    print("   " * (indent + 1) + str(v))
            elif isinstance(value, (dict, collections.OrderedDict)):
                print_fmt(value, indent + 1)
            else:
                print(value)

    print()
    print_fmt(out)
    print()
