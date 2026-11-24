'''
Reply framing shared by targetclid and the targetcli client.

This file is part of targetcli.
Copyright (c) 2026 by Red Hat, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.

A reply is MAGIC followed by any number of records and a single END tag.
Each record is a one-byte stream tag (STDOUT or STDERR), a 4-byte
big-endian payload length in bytes, and the UTF-8 encoded payload.
Records are sent in the order the output was produced, so the client can
replay stdout and stderr interleaved exactly as the commands wrote them.
'''

import io
import struct
from itertools import groupby

MAGIC = b'TCD\x02'
STDOUT = b'O'
STDERR = b'E'
END = b'.'

_LENGTH = struct.Struct('!I')


class ProtocolError(Exception):
    '''The peer sent something that is not a valid reply.'''


class StreamRecorder(io.TextIOBase):
    '''
    Write-only text stream that appends each write to a shared list as a
    (tag, text) record. encode_reply() merges consecutive records of the
    same stream, so writes here stay cheap however much output there is.
    '''

    def __init__(self, tag, records):
        super().__init__()
        self._tag = tag
        self._records = records

    def writable(self):
        return True

    def write(self, text):
        if text:
            self._records.append((self._tag, text))
        return len(text)


def encode_reply(records):
    '''Serialize a list of (tag, text) records into a reply.'''
    parts = [MAGIC]
    for tag, group in groupby(records, key=lambda record: record[0]):
        payload = "".join(text for _, text in group).encode()
        parts += [tag, _LENGTH.pack(len(payload)), payload]
    parts.append(END)
    return b''.join(parts)


def _recv_exact(sock, size):
    buf = bytearray()
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise ProtocolError("connection closed by targetclid")
        buf += chunk
    return bytes(buf)


def read_reply(sock):
    '''Read one reply from sock and return it as a list of (tag, text).'''
    if _recv_exact(sock, len(MAGIC)) != MAGIC:
        raise ProtocolError("unexpected reply from targetclid; "
                            "it may be from a different targetcli version, "
                            "please restart targetclid")
    records = []
    while True:
        tag = _recv_exact(sock, 1)
        if tag == END:
            return records
        if tag not in (STDOUT, STDERR):
            raise ProtocolError(f"unknown record tag {tag!r} from targetclid")
        (length,) = _LENGTH.unpack(_recv_exact(sock, _LENGTH.size))
        try:
            text = _recv_exact(sock, length).decode()
        except UnicodeDecodeError as e:
            raise ProtocolError(f"invalid UTF-8 from targetclid: {e}") from e
        records.append((tag, text))
