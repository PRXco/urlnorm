#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
urlnorm.py - URL normalization routines

urlnorm normalizes a URL by:
  * lowercasing the scheme and hostname
  * converting the hostname to IDN format
  * taking out default port if present (e.g., http://www.foo.com:80/)
  * collapsing the path (./, ../, //, etc)
  * removing the last character in the hostname if it is '.'
  * unescaping any percent escape sequences (where possible)
  * upercase percent escape (ie: %3f => %3F)
  * converts spaces to %20
  * converts ip encoded as an integer to dotted quad notation 

Available functions:
  norm - given a URL (string), returns a normalized URL
  norm_netloc
  norm_path
  unquote_path
  unquote_params
  unquote_qs
  unquote_fragment


CHANGES:
1.1.4 - unescape " " in params, query string, and fragments
1.1.3 - don't escape " " in path
1.1.2 - leave %20 as %20, collate ' ' to %20, leave '+' as '+'
1.1 - collate %20 and ' ' to '+'
1.1 - fix unescaping of parameters
1.1 - added int2ip
1.0.1 - fix problem unescaping %23 and %20 in query string
1.0 - new release
0.94 - idna handling, unescaping querystring, fragment, add ws + wss ports
0.92 - unknown schemes now pass the port through silently
0.91 - general cleanup
     - changed dictionaries to lists where appropriate
     - more fine-grained authority parsing and normalisation    
"""

__license__ = """
Copyright (c) 1999-2002 Mark Nottingham <mnot@pobox.com>
Copyright (c) 2010 Jehiah Czebotar <jehiah@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# also update in setup.py
__version__ = "1.1.4"

import re
import sys

if sys.version_info[0] == 3:
    PY2 = False
    PY3 = True
elif sys.version_info[0] == 2:
    PY2 = True
    PY3 = False


if PY3:
    from urllib.parse import urlparse, urlunparse as urlunparse_py3
    xrange = range

    def range(*args, **kwargs):
        return list(xrange(*args, **kwargs))

    unichr = chr

    def chr(i):
        return bytes([i])

    unicode = str

    def urlunparse(parts):
        return _utf8(urlunparse_py3(parts))

    def lower(s):
        return s.lower()

elif PY2:
    from __builtin__ import unichr
    from urlparse import urlparse, urlunparse

    bytes = str

    PY3 = False
    PY2 = True
    from string import lower


def re_match(re_obj, s):
    if PY2:
        return re_obj.match(s)
    elif PY3:
        return re_obj.match(_unicode(s))


def bytes_idx(s, idx):
    """
    In Python2:
    >>> b'abc'[0]
    b'a'

    In Python3:
    >>> b'abc'[0]
    97

    This normalizes to the Python 2 version.
    """
    assert isinstance(idx, int)
    if PY2:
        # indexing a bytes object in PY2
        # returns a single-character bytestring.
        return s[idx]
    elif PY3:
        # indexing a bytes object in PY3 returns
        # an int.
        return chr(s[idx])


class InvalidUrl(Exception):
    pass

_server_authority = re.compile('^(?:([^\@]+)\@)?([^\:\[\]]+|\[[a-fA-F0-9\:\.]+\])(?:\:(.*?))?$')
_default_port = {
    b'http': b'80',
    b'itms': b'80',
    b'ws': b'80',
    b'https': b'443',
    b'wss': b'443',
    b'gopher': b'70',
    b'news': b'119',
    b'snews': b'563',
    b'nntp': b'119',
    b'snntp': b'563',
    b'ftp': b'21',
    b'telnet': b'23',
    b'prospero': b'191',
}
_relative_schemes = set([
    b'http',
    b'https',
    b'ws',
    b'wss',
    b'itms',
    b'news',
    b'snews',
    b'nntp',
    b'snntp',
    b'ftp',
    b'file',
    b''
])

params_unsafe_list = b'?=+%#;'
qs_unsafe_list = b'?&=+%#'
fragment_unsafe_list = b'+%#'
path_unsafe_list = b'/?;%+#'

_hextochr = dict((b'%02x' % i, chr(i)) for i in range(256))
_hextochr.update((b'%02X' % i, chr(i)) for i in range(256))


def unquote_path(s):
    """
    :rtype: unicode
    """
    return unquote_safe(s, path_unsafe_list)


def unquote_params(s):
    """
    :rtype: unicode
    """
    return unquote_safe(s, params_unsafe_list)


def unquote_qs(s):
    """
    :rtype: unicode
    """
    return unquote_safe(s, qs_unsafe_list)


def unquote_fragment(s):
    """
    :rtype: unicode
    """
    return unquote_safe(s, fragment_unsafe_list)


def unquote_safe(s, unsafe_list):
    """unquote percent escaped string except for percent escape sequences that are in unsafe_list"""
    # note: this build utf8 raw strings ,then does a .decode('utf8') at the end.
    # as a result it's doing .encode('utf8') on each block of the string as it's processed.
    res = _utf8(s).split(b'%')
    for i in xrange(1, len(res)):
        item = res[i]
        try:
            raw_chr = _hextochr[item[:2]]
            if raw_chr in unsafe_list or ord(raw_chr) < 20:
                # leave it unescaped (but uppercase the percent escape)
                res[i] = b'%' + item[:2].upper() + item[2:]
            else:
                res[i] = raw_chr + item[2:]
        except KeyError:
            res[i] = b'%' + item
        except UnicodeDecodeError:
            # note: i'm not sure what this does
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    o = b"".join(res)
    return _unicode(o)


def norm(url):
    """given a string URL, return its normalized/unicode form"""
    url = _unicode(url)  # operate on unicode strings
    normalized_tuple = norm_tuple(*urlparse(url))
    return urlunparse(normalized_tuple)


def norm_tuple(scheme, authority, path, parameters, query, fragment):
    """given individual url components, return its normalized form"""

    scheme = lower(scheme)
    if not scheme:
        raise InvalidUrl('missing URL scheme')
    authority = norm_netloc(scheme, authority)
    if not authority:
        raise InvalidUrl('missing netloc')
    path = norm_path(scheme, path)
    # TODO: put query in sorted order; or at least group parameters together
    # Note that some websites use positional parameters or the name part of a query so this would break the internet
    # query = urlencode(parse_qs(query, keep_blank_values=1), doseq=1)
    parameters = unquote_params(parameters)
    query = unquote_qs(query)
    fragment = unquote_fragment(fragment)
    return (scheme, authority, path, parameters, query, fragment)


def norm_path(scheme, path):
    scheme = _utf8(scheme)
    path = _utf8(path)

    if scheme in _relative_schemes:
        # resolve `/../` and `/./` and `//` components in path as appropriate
        i = 0
        parts = []
        start = 0
        while i < len(path):
            if bytes_idx(path, i) == b"/" or i == len(path) - 1:
                chunk = path[start:i+1]
                start = i + 1
                if chunk in [b"", b"/", b".", b"./"]:
                    # do nothing
                    pass
                elif chunk in [b"..", b"../"]:
                    if len(parts):
                        parts = parts[:len(parts)-1]
                    else:
                        parts.append(chunk)
                else:
                    parts.append(chunk)
            i += 1
        path = b"/" + (b"".join(parts))

    # return unicode
    path = unquote_path(path)
    if not path:
        return u'/'

    return path

MAX_IP = 0xffffffff


def int2ip(ipnum):
    assert isinstance(ipnum, int)
    if MAX_IP < ipnum or ipnum < 0:
        raise TypeError("expected int between 0 and %d inclusive" % MAX_IP)
    ip1 = ipnum >> 24
    ip2 = ipnum >> 16 & 0xFF
    ip3 = ipnum >> 8 & 0xFF
    ip4 = ipnum & 0xFF
    return b"%d.%d.%d.%d" % (ip1, ip2, ip3, ip4)


def norm_netloc(scheme, netloc):
    if not netloc:
        return netloc
    match = re_match(_server_authority, netloc)
    if not match:
        raise InvalidUrl('no host in netloc %r' % netloc)

    userinfo, host, port = match.groups()

    # For py2/py3 compat
    userinfo = _utf8(userinfo)
    host = _utf8(host)
    port = _utf8(port)
    scheme = _utf8(scheme)
    netloc = _utf8(netloc)

    # catch a few common errors:
    if host.isdigit():
        try:
            host = int2ip(int(host))
        except TypeError:
            raise InvalidUrl('host %r does not escape to a valid ip' % host)
    if bytes_idx(host, -1) == b'.':
        host = host[:-1]

    # bracket check is for ipv6 hosts
    if b'.' not in host and not (bytes_idx(host, 0) == b'[' and bytes_idx(host, -1) == b']'):
        raise InvalidUrl('host %r is not valid' % host)

    authority = lower(host)
    if b'xn--' in authority:
        subdomains = [_idn(subdomain) for subdomain in authority.split(b'.')]
        authority = b'.'.join(subdomains)

    if userinfo:
        authority = b"%s@%s" % (userinfo, authority)
    if port and port != _default_port.get(_utf8(scheme), None):
        authority = b"%s:%s" % (authority, port)
    return _unicode(authority)


def _idn(subdomain):
    """
    If bytestring `subdomain` is punycode-encoded (see IDNA), decodes using IDNA,
    and returns the decoded string as a UTF8 bytestring.

    Otherwise returns the bytestring as is.
    """
    if subdomain.startswith(b'xn--'):
        try:
            subdomain = subdomain.decode('idna')
        except UnicodeError:
            raise InvalidUrl('Error converting subdomain %r to IDN' % subdomain)
        else:
            return _utf8(subdomain)
    return subdomain


def _utf8(value):
    if isinstance(value, unicode):
        return value.encode("utf-8")
    return value


def _unicode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
