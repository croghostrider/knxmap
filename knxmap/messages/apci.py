import logging
import struct

LOGGER = logging.getLogger(__name__)

from knxmap.data.constants import _CEMI_APCI_TYPES, CEMI_APCI_TYPES


class Apci:
    def __init__(self, apci_type=None, apci_data=None, data=None):
        if isinstance(apci_type, str):
            apci_type = CEMI_APCI_TYPES.get(apci_type)
        self.apci_type = apci_type
        self.apci_data = apci_data
        self.data = data

    def __repr__(self):
        return f"{self.__class__.__name__} apci_type: {_CEMI_APCI_TYPES.get(self.apci_type)}, apci_data: {self.apci_data}"

    @staticmethod
    def _unpack_stream(fmt, stream):
        try:
            buf = stream.read(struct.calcsize(fmt))
            return struct.unpack(fmt, buf)[0]
        except struct.error as e:
            LOGGER.exception(e)

    def pack(self):
        # TODO: nasty hacks
        apci = 0
        apci_type_len = len(bin(self.apci_type)[2:])
        if apci_type_len <= 4:
            while len(bin(self.apci_type)[2:]) < 8:
                self.apci_type *= 2
        elif apci_type_len < 10:
            while len(bin(self.apci_type)[2:]) < 10:
                self.apci_type *= 2
        apci |= self.apci_type << 0
        if self.apci_data:
            i = 0
            data_space = 10 - apci_type_len
            while data_space > 0:
                apci |= ((self.apci_data >> i) & 1) << i
                i += 1
                data_space -= 1
                # apci |= self.apci_data << 0
        # apci = struct.pack('!H', apci)
        return apci

    def unpack(self, data=None):
        data = data or self.data
        if len(data) == 1:
            data.extend([0])
        # assert len(data) >= 2, 'APCI data too short (only %d bytes)' % len(data)
        self.apci_type = 0
        self.apci_type |= ((data[1] >> 6) & 1) << 0
        self.apci_type |= ((data[1] >> 7) & 1) << 1
        self.apci_type |= ((data[0] >> 0) & 1) << 2
        self.apci_type |= ((data[0] >> 1) & 1) << 3
        if self.apci_type in CEMI_APCI_TYPES.values():
            self.apci_data = 0
            self.apci_data |= ((data[1] >> 0) & 1) << 0
            self.apci_data |= ((data[1] >> 1) & 1) << 1
            self.apci_data |= ((data[1] >> 2) & 1) << 2
            self.apci_data |= ((data[1] >> 3) & 1) << 3
            self.apci_data |= ((data[1] >> 4) & 1) << 4
            self.apci_data |= ((data[1] >> 5) & 1) << 5
        else:
            self.apci_type <<= 2
            self.apci_type |= ((data[1] >> 4) & 1) << 0
            self.apci_type |= ((data[1] >> 5) & 1) << 1
            if self.apci_type in CEMI_APCI_TYPES.values():
                self.apci_data = 0
                self.apci_data |= ((data[1] >> 0) & 1) << 0
                self.apci_data |= ((data[1] >> 1) & 1) << 1
                self.apci_data |= ((data[1] >> 2) & 1) << 2
                self.apci_data |= ((data[1] >> 3) & 1) << 3
            else:
                self.apci_type <<= 4
                self.apci_type |= ((data[1] >> 0) & 1) << 0
                self.apci_type |= ((data[1] >> 1) & 1) << 1
                self.apci_type |= ((data[1] >> 2) & 1) << 2
                self.apci_type |= ((data[1] >> 3) & 1) << 3
