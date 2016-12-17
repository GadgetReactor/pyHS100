from __future__ import absolute_import
from __future__ import unicode_literals

import json
import socket
import logging

_LOGGER = logging.getLogger(__name__)


class TPLinkSmartHomeProtocol:
    """
    Implementation of the TP-Link Smart Home Protocol

    Encryption/Decryption methods based on the works of
    Lubomir Stroetmann and Tobias Esser

    https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/
    https://github.com/softScheck/tplink-smartplug/

    which are licensed under the Apache License, Version 2.0
    http://www.apache.org/licenses/LICENSE-2.0
    """
    initialization_vector = 171

    @staticmethod
    def query(host, request, port=9999, socket_type=socket.SOCK_STREAM):
        """
        Request information from a TP-Link SmartHome Device and return the
        response.

        :param str host: ip address of the device
        :param int port: port on the device (default: 9999)
        :param request: command to send to the device (can be either dict or
        json string)
        :return:
        """
        if isinstance(request, dict):
            request = json.dumps(request)

        encrypted_req = TPLinkSmartHomeProtocol.encrypt(request)

        sock = socket.socket(socket.AF_INET, socket_type)

        if socket_type == socket.SOCK_STREAM:
            sock.connect((host, port))
            sock.send(encrypted_req)
        elif socket_type == socket.SOCK_DGRAM:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.sendto(encrypted_req[4:], (host, port))

        _LOGGER.debug("> (%i) %s", len(request), request)

        buffer = bytes()
        while True:
            chunk = sock.recv(4096)
            buffer += chunk
            if not chunk:
                break

        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        response = TPLinkSmartHomeProtocol.decrypt(buffer[4:])
        _LOGGER.debug("< (%i) %s", len(response), response)

        return json.loads(response)

    @staticmethod
    def discover():
        disc_query = {"system": {"get_sysinfo": None}, "emeter": {"get_realtime": None}}
        bcast = "255.255.255.255"
        for res in  TPLinkSmartHomeProtocol.query(bcast, json.dumps(disc_query), socket_type=socket.SOCK_DGRAM):
            yield res


    @staticmethod
    def encrypt(request):
        """
        Encrypt a request for a TP-Link Smart Home Device.

        :param request: plaintext request data
        :return: ciphertext request
        """
        key = TPLinkSmartHomeProtocol.initialization_vector
        buffer = bytearray(4)  # 4 nullbytes

        for char in request:
            cipher = key ^ ord(char)
            key = cipher
            buffer.append(cipher)

        return buffer

    @staticmethod
    def decrypt(ciphertext):
        """
        Decrypt a response of a TP-Link Smart Home Device.

        :param ciphertext: encrypted response data
        :return: plaintext response
        """
        key = TPLinkSmartHomeProtocol.initialization_vector
        buffer = []

        ciphertext = ciphertext.decode('latin-1')

        for char in ciphertext:
            plain = key ^ ord(char)
            key = ord(char)
            buffer.append(chr(plain))

        plaintext = ''.join(buffer)

        return plaintext
