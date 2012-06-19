#! /usr/bin/python3

# A BitTorrent metainfo file and magnet link generator
# Copyright (C) Tanguy Ortolo <tanguy+gentorrent@ortolo.eu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.



import argparse
import locale
import re
import os
from io import BytesIO
from collections import OrderedDict
from hashlib import sha1, md5
from urllib.parse import urlencode
from time import time
from os import path

os_sep = os.sep.encode('ascii')


name = "gentorrent"
version = "1.0"
fullname = "%s %s" % (name, version)


def bdecode(data, offset=0):
    """Decode data, that must be a bytes or bytearray, according to the
    BitTorrent bencoding.

    Positional argument:
    data   -- data to bdecode

    Optional arguments:
    offset -- where to start decoding (default to zero)

    Return: a composition of bytes, int, dictionary or list

    >>> bdecode("string")
    Traceback (most recent call last):
        ...
    TypeError: only bytes-like objects and IO readers are supported

    >>> bdecode(b'4:spam')
    b'spam'
    >>> bdecode(b'i3e')
    3
    >>> bdecode(b'l4:spam4:eggse')
    [b'spam', b'eggs']
    >>> sorted(bdecode(b'd3:cow3:moo4:spam4:eggse').items())
    [(b'cow', b'moo'), (b'spam', b'eggs')]
    >>> sorted(bdecode(b'd4:spaml1:a1:bee').items())
    [(b'spam', [b'a', b'b'])]
    >>> sorted(bdecode(b'd9:publisher3:bob17:publisher-webpage15:www.example.com18:publisher.location4:homee').items())
    [(b'publisher', b'bob'), (b'publisher-webpage', b'www.example.com'), (b'publisher.location', b'home')]

    >>> bdecode(b'6:4:spam')
    b'4:spam'

    >>> bdecode(Bencoded(b'4:spam'))
    b'spam'

    """
    def aux(data, magic=None):
        digits = b'0123456789'
        if not magic:
            magic = data.read(1)
        if magic in digits:
            # This is a string
            length = 0
            # Compute the length
            current = magic
            while current and current in digits:
                length *= 10
                length += int(current)
                current = data.read(1)
            # We have just read the length/string separator byte b':'
            if current != b':':
                # Separator byte not found
                raise ValueError("this is not a valid bencoded string (syntax is b'<length>:<string>')")
            # We are now at the first byte of the string
            s = data.read(length)
            if len(s) != length:
                # EOF reached before the end of the bencoded string
                raise ValueError("premature end of a bencoded string")
            return s
        elif magic == b'i':
            # This is an int
            i = 0
            current = data.read(1)  # skip the magic byte b'i'
            while current and current in digits:
                i *= 10
                i += int(current)
                current = data.read(1)
            # We have just read the end byte b'e'
            if current != b'e':
                # End byte b'e' not found, perhaps EOF
                raise ValueError("this is not a valid bencoded int (syntax is b'i<int>e')")
            return i
        elif magic == b'd':
            # This is a dict
            current = data.read(1)  # skip the magic byte b'd'
            d = {}
            while current and current != b'e':
                key = aux(data, current)
                value = aux(data)
                d[key] = value
                current = data.read(1)
            # We have just read the end byte b'e'
            if current != b'e':
                # End byte b'e' not found, perhaps EOF
                raise ValueError("this is not a valid bencoded dict (syntax is b'd<keys and values>e')")
            return d
        elif magic in b'l':
            # This is a list
            current = data.read(1)  # skip the magic byte b'l'
            l = []
            while current and current != b'e':
                l.append(aux(data, current))
                current = data.read(1)
            # We have just read the end byte b'e'
            if current != b'e':
                # End byte b'e' not found, perhaps EOF
                raise ValueError("this is not a valid bencoded list (syntax is b'l<values>e')")
            return l
        else:
            raise ValueError("this is not valid bencoded data")
    if not hasattr(data, 'read'):
        try:
            data = BytesIO(data)
        except TypeError:
            raise TypeError("only bytes-like objects and IO readers are supported")
    return aux(data)


def bencode(data, buf=None):
    """Encode data, that can be composed of bytes, int, dictionary or list,
    according to the BitTorrent bencoding.

    Positional argument:
    data -- data to bencode

    Optional argument:
    buf  -- buffer to which append the bencoded data (by default, an empty
            buffer is created)

    >>> bencode("string")
    Traceback (most recent call last):
        ...
    TypeError: str are not supported, please encode to bytes

    >>> bencode(b"spam")
    bytearray(b'4:spam')
    >>> bencode(3)
    bytearray(b'i3e')
    >>> bencode([b"spam", b"eggs"])
    bytearray(b'l4:spam4:eggse')
    >>> bencode({b"cow": b"moo", b"spam": b"eggs"})
    bytearray(b'd3:cow3:moo4:spam4:eggse')
    >>> bencode({b"spam": [b"a", b"b"]})
    bytearray(b'd4:spaml1:a1:bee')
    >>> bencode({b"publisher": b"bob", b"publisher-webpage": b"www.example.com", b"publisher.location": b"home"})
    bytearray(b'd9:publisher3:bob17:publisher-webpage15:www.example.com18:publisher.location4:homee')

    >>> bencode(b'4:spam')
    bytearray(b'6:4:spam')

    >>> bencode(Bencoded(b'4:spam'))
    bytearray(b'4:spam')

    """
    if not buf:
        buf = BencodedArray()
    if isinstance(data, str):
        raise TypeError("str are not supported, please encode to bytes")
    elif isinstance(data, Bencoded) or isinstance(data, BencodedArray):
        buf.extend(data)
    elif isinstance(data, bytes) or isinstance(data, bytearray):
        buf.extend(("%d" % len(data)).encode('ascii'))
        buf.extend(b':')
        buf.extend(data)
    elif isinstance(data, int):
        buf.extend(b'i')
        buf.extend(("%d" % data).encode('ascii'))
        buf.extend(b'e')
    elif hasattr(data, 'keys'):
        # This is a mapping
        buf.extend(b'd')
        for key in sorted(data.keys()):
            bencode(key, buf)
            bencode(data[key], buf)
        buf.extend(b'e')
    elif hasattr(data, '__iter__'):
        # This is a list
        buf.extend(b'l')
        for elt in data:
            bencode(elt, buf)
        buf.extend(b'e')
    else:
        raise TypeError("only compositions of bytes, int, dictionary and list are supported")
    return buf


class Bencoded(bytes):
    """A bytes string encoded according to the BitTorrent bencoding

    This is a dummy class, that exists only to distinguish between strings
    bencoded or not. As such, it can be used with the bytes interface.

    >>> Bencoded(b'foobar')
    b'foobar'
    >>> Bencoded(bytearray(b'foobar'))
    b'foobar'

    """
    pass


class BencodedArray(bytearray):
    """A bytearray string encoded according to the BitTorrent bencoding

    This is a dummy class, that exists only to distinguish between strings
    bencoded or not. As such, it can be used with the bytearray interface.

    >>> BencodedArray(b'foobar')
    bytearray(b'foobar')
    >>> BencodedArray(bytearray(b'foobar'))
    bytearray(b'foobar')

    """
    pass


class Metainfo(dict):

    def __init__(self, filename, announce=None, nodes=None, httpseeds=None,
                 url_list=None, comment=None, piece_length=256*1024,
                 private=False, md5sum=False, merkle=False):
        """Create a BitTorrent metainfo structure (cf. BEP-3).

        Positional arguments:
        filename -- name of the file or directory to be distributed

        Keyword arguments:
        announce     -- list of list of tracker announce URL, in the format
                        [["main1", "main2", …], ["backup1", "backup2", …], …]
                        (cf. BEP-12)
        nodes        -- list of DHT nodes, in the format [["host", port], …]
                        (cf. BEP-5)
        httpseeds    -- list of HTTP seed URLs, in the format ["url", "url", …]
                        (cf. BEP-17)
        url_list     -- list of HTTP/FTP seeding URLs (GetRight style), in the
                        format ["url", "url", …] (cf. BEP-19)
        comment      -- optional comment
        piece_length -- lenght (in bytes) of the pieces into which the file(s)
                        will be split (defaults to 256 kibi, cf. BEP-3)
        private      -- forbid DHT and peer exchange (optional, defaults to False,
                        cf. BEP-27)
        md5sum       -- include the MD5 hash of the files (optional, defaults to False)
        merkle       -- generate a Merkle torrent (defaults to False, cf. BEP-30)

        Return: a dictionary-like structure, ready to be bencoded

        Notes:
        * You should provide either an announce list of liste, or a nodes list.
        * All strings given should be bytes, not str.

        """
        super().__init__()
        if announce:
            self[b"announce"] = announce[0][0]
            if len(announce[0]) > 1 or len(announce) > 1 :
                self[b"announce-list"] = announce
        self.announce = announce
        if nodes:
            self[b"nodes"] = nodes
        self.nodes = nodes
        if httpseeds:
            self[b"httpseeds"] = httpseeds
        self.httpseeds = httpseeds
        if url_list:
            self[b"url-list"] = url_list
        self.url_list = url_list
        self[b"creation date"] = int(time())
        if comment:
            self[b"comment"] = comment
        self[b"created by"] = fullname.encode('utf-8')
        # Now we build the info dictionnary
        self[b"info"] = {}
        info = self[b"info"]
        info[b"piece length"] = piece_length
        pieces = bytearray()
        if private:
            info[b"private"] = 1
        info[b"name"] = path.basename(path.normpath(filename))
        if path.isfile(filename):
            info[b"length"] = path.getsize(filename)
            if md5sum:
                md5sum = md5()
            with open(filename, mode='rb') as f:
                while True:
                    chunk = f.read(piece_length)
                    if len(chunk) == 0:
                        # We exactly reached the end at last iteration
                        break
                    pieces.extend(sha1(chunk).digest())
                    if md5sum:
                        md5sum.update(chunk)
                    if len(chunk) < piece_length:
                        # We have reached the end
                        break
            if md5sum:
                info[b"md5sum"] = md5sum.hexdigest().encode('ascii')
        elif path.isdir(filename):
            dirname = filename
            info[b"files"] = []
            files = info[b"files"]
            incomplete_chunk = bytearray()
            for dirpath, dirnames, filenames in os.walk(dirname):
                for filename in filenames:
                    filedict = {}
                    filename = path.join(dirpath, filename)
                    filedict[b"path"] = path.relpath(filename, dirname).split(os_sep)
                    filedict[b"length"] = path.getsize(filename)
                    if md5sum:
                        md5sum = md5()
                    with open(filename, mode='rb') as f:
                        while True:
                            chunk = f.read(piece_length - len(incomplete_chunk))
                            if len(chunk) == 0:
                                # We exactly reached the end at last iteration
                                break
                            if len(incomplete_chunk) + len(chunk) < piece_length:
                                # We have reached the end and got an incomplete chunk
                                incomplete_chunk += chunk
                                if md5sum:
                                    md5sum.update(chunk)
                                break
                            # We have got a complete chunk
                            pieces.extend(sha1(incomplete_chunk + chunk).digest())
                            incomplete_chunk = bytearray()
                            if md5sum:
                                md5sum.update(chunk)
                    if md5sum:
                        filedict[b"md5sum"] = md5sum.hexdigest().encode('ascii')
                    files.append(filedict)
            if incomplete_chunk:
                # We have an incomplete chunk left to hash
                pieces.extend(sha1(incomplete_chunk).digest())
        if merkle:
            # Merkle torrent: we calculate the Merkle tree's root node
            # to use in in place of the pieces.
            padding = 20 * b"\0"
            # Reduce the hashes until there is only one left
            # (hashes are 20 bytes long).
            while len(pieces) > 20:
                if len(pieces) % 40:
                    # There is an odd number of pieces: we padd it with
                    # zeros… or recursive hashes of zeros as we are
                    # clibing the tree, cf. BEP-30.
                    pieces.extend(padding)
                # Hash the hashes by two and store the result in place
                for i in range(0, len(pieces) // 2, 20):
                    pieces[i:i + 20] = sha1(pieces[2*i:2*i + 40]).digest()
                # Next level…
                # Truncate the hash list as all our new pieces are now only
                # in its first half.
                del pieces[len(pieces)//2:]
                # The padding at the new level is the result of hashing two
                # padding pieces together, cf. BEP-30.
                padding = sha1(2 * padding).digest()
            info[b"root hash"] = pieces
        else:
            # Regular torrent: we use the pieces directly
            info[b"pieces"] = pieces
        # Shortcuts
        self.info = info
        self.__infohash = None
        self.name = info[b"name"]
        if b"length" in info :
            self.length = info[b"length"]
        else :
            self.length = None

    @property
    def infohash(self):
        if not self.__infohash:
            self.__infohash = sha1(bencode(self.info)).hexdigest()
        return self.__infohash

    def magnet(self):
        params = OrderedDict()
        params[b'dn'] = self.name
        if self.length :
            params[b'xl'] = ("%d" % self.length).encode('ascii')
        params[b'xt'] = self.infohash
        params[b'tr'] = []
        if self.announce:
            for tracker_list in self.announce:
                for tracker in tracker_list:
                    params[b'tr'].append(tracker)
        params[b'as'] = []
        if self.url_list:
            for url in self.url_list:
                params[b'as'].append(url)
        return "magnet:?%s" % urlencode(params, doseq=True)


def main():
    locale.setlocale(locale.LC_ALL, '')
    encoding = locale.getpreferredencoding()
    def decode(string):
        return string.encode(encoding)
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='Generate a BitTorrent metainfo file and magnet link',
                                     usage='%(prog)s {--announce URL|--nodes HOST:PORT [HOST:PORT ...]} \
-- FILE',
                                     epilog="""Typical usage for a tracked torrent:
%(prog)s --announce http://torrent.example.com:6969/announce -- file

For a trackerless (DHT) torrent:
%(prog)s --nodes foo.example.com:51413 \\
                 192.2.0.42:51413 \\
                 [2001:db8::42]:51413 -- file""")
    parser.add_argument('--announce', '-a', action='append', nargs='+',
                        type=decode, metavar="URL", help='list of tracker URLs;\
                        use several times to define backup trackers')
    parser.add_argument('--nodes', '-n', action='store', nargs='+', default=[],
                        type=decode, metavar="HOST:PORT",
                        help='list of known good peers for DHT initialization')
    parser.add_argument('--httpseeds', action='store', nargs='+', default=[],
                        type=decode, metavar='URL', help='list of HTTP seed URLs\
                        (BEP-17)')
    parser.add_argument('--url-list', action='store', nargs='+', default=[],
                        type=decode, metavar='URL', help='list of HTTP/FTP\
                        seeding URLs (GetRight style, BEP-19)')
    parser.add_argument('--comment', '-c', type=decode,
                        help='optional comment added to the torrent')
    parser.add_argument('--piece-length', '-l', type=int, metavar='N',
                        help='lenght (in bytes) of the pieces into which the\
                        file(s) will be split (defaults to 256 kibi)')
    parser.add_argument('--md5sum', action='store_true',
                        help='include the MD5 hash of the files: this is not\
                        required and requires more computing')
    parser.add_argument('--private', action='store_true',
                        help='generate a private torrent, forbidding DHT and\
                        peer exchange (BEP-27)')
    parser.add_argument('--merkle', action='store_true',
                        help='create a Merkle torrent (BEP-30): this allows to\
                        produces a very light file but requires more computing\
                        and is not widely supported by clients')
    parser.add_argument('--output', '-o', type=decode, default=None,
                        metavar='FILE', help='output file (defaults to the input\
                        file with .torrent appended)')
    parser.add_argument('filename', type=decode, metavar='FILE',
                        help='file or directory to process')
    prog_args = parser.parse_args()
    func_args = {}
    if prog_args.announce:
        func_args['announce'] = prog_args.announce
    if prog_args.nodes:
        address6 = re.compile(b'^\[([\da-fA-F:]+)\]:(\d+)$')
        address4 = re.compile(b'^([\d\.]+):(\d+)$')
        addressname = re.compile(b'^(.+):(\d+)$$')
        nodes = []
        for node in prog_args.nodes:
            match = address6.match(node) or address4.match(node) or addressname.match(node)
            if not match:
                parser.error('invalid node address specification')
            address = match.group(1)
            port = int(match.group(2))
            nodes.append((address, port))
        func_args['nodes'] = nodes
    if prog_args.httpseeds:
        func_args['httpseeds'] = prog_args.httpseeds
    if prog_args.url_list:
        func_args['url_list'] = prog_args.url_list
    if prog_args.comment:
        func_args['comment'] = prog_args.comment
    if prog_args.piece_length:
        func_args['piece_length'] = prog_args.piece_length
    if prog_args.md5sum:
        func_args['md5sum'] = True
    if prog_args.private:
        func_args['private'] = True
    if prog_args.merkle:
        func_args['merkle'] = True
    filename = prog_args.filename.rstrip(os_sep)
    if prog_args.output:
        infoname = prog_args.output
    else:
        infoname = filename + b'.torrent'
    with open(infoname, 'wb') as infofile:
        metainfo = Metainfo(prog_args.filename, **func_args)
        infofile.write(bencode(metainfo))
    print("Magnet link: <%s>" % metainfo.magnet())


if __name__ == '__main__':
    main()
