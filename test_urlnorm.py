"""
this is a py.test test file
"""
from __future__ import print_function, absolute_import, unicode_literals
import urlnorm
from urlnorm import _unicode


def assert_py2_str_eq(a, b):
    try:
        assert a == b
    except AssertionError as e:
        if type(a) != type(b):
            unicode_a = a.decode('utf-8') if isinstance(a, bytes) else a
            unicode_b = b.decode('utf-8') if isinstance(b, bytes) else b
            assert unicode_a == unicode_b
        else:
            raise e



def pytest_generate_tests(metafunc):
    if metafunc.function in [test_norms]:
        """ test suite; some taken from RFC1808. Run with py.test"""
        tests = {
            b'http://1113982867/':            b'http://66.102.7.147/', # ip dword encoding
            b'http://www.thedraymin.co.uk:/main/?p=308': b'http://www.thedraymin.co.uk/main/?p=308', # empty port
            b'http://www.foo.com:80/foo':     b'http://www.foo.com/foo',
            b'http://www.foo.com:8000/foo':   b'http://www.foo.com:8000/foo',
            b'http://www.foo.com./foo/bar.html': b'http://www.foo.com/foo/bar.html',
            b'http://www.foo.com.:81/foo':    b'http://www.foo.com:81/foo',
            b'http://www.foo.com/%7ebar':     b'http://www.foo.com/~bar',
            b'http://www.foo.com/%7Ebar':     b'http://www.foo.com/~bar',
            b'ftp://user:pass@ftp.foo.net/foo/bar': b'ftp://user:pass@ftp.foo.net/foo/bar',
            b'http://USER:pass@www.Example.COM/foo/bar': b'http://USER:pass@www.example.com/foo/bar',
            b'http://www.example.com./':      b'http://www.example.com/',
            b'http://test.example/?a=%26&b=1': b'http://test.example/?a=%26&b=1', # should not un-encode the & that is part of a parameter value
            b'http://test.example/?a=%e3%82%82%26': b'http://test.example/?a=\xe3\x82\x82%26'.decode('utf8'), # should return a unicode character
            # note: this breaks the internet for parameters that are positional (stupid nextel) and/or don't have an = sign
            # 'http://test.example/?a=1&b=2&a=3': 'http://test.example/?a=1&a=3&b=2', # should be in sorted/grouped order
            
            # 'http://s.xn--q-bga.de/':       'http://s.q\xc3\xa9.de/'.decode('utf8'), # should be in idna format
            b'http://test.example/?':        b'http://test.example/', # no trailing ?
            b'http://test.example?':       b'http://test.example/', # with trailing /
            b'http://a.COM/path/?b&a' : b'http://a.com/path/?b&a',
            # test utf8 and unicode
            u'http://XBLA\u306eXbox.com': b'http://xbla\xe3\x81\xaexbox.com/'.decode('utf8'),
            u'http://XBLA\u306eXbox.com'.encode('utf8'): b'http://xbla\xe3\x81\xaexbox.com/'.decode('utf8'),
            u'http://XBLA\u306eXbox.com': b'http://xbla\xe3\x81\xaexbox.com/'.decode('utf8'),
            # test idna + utf8 domain
            # u'http://xn--q-bga.XBLA\u306eXbox.com'.encode('utf8'): 'http://q\xc3\xa9.xbla\xe3\x81\xaexbox.com'.decode('utf8'),
            b'http://ja.wikipedia.org/wiki/%E3%82%AD%E3%83%A3%E3%82%BF%E3%83%94%E3%83%A9%E3%83%BC%E3%82%B8%E3%83%A3%E3%83%91%E3%83%B3': b'http://ja.wikipedia.org/wiki/\xe3\x82\xad\xe3\x83\xa3\xe3\x82\xbf\xe3\x83\x94\xe3\x83\xa9\xe3\x83\xbc\xe3\x82\xb8\xe3\x83\xa3\xe3\x83\x91\xe3\x83\xb3'.decode('utf8'),
            b'http://test.example/\xe3\x82\xad': b'http://test.example/\xe3\x82\xad',
            
            # check that %23 (#) is not escaped where it shouldn't be
            b'http://test.example/?p=%23val#test-%23-val%25': b'http://test.example/?p=%23val#test-%23-val%25',
            # check that %25 is not unescaped to %
            b'http://test.example/%25/?p=val%25ue': b'http://test.example/%25/?p=val%25ue',
            b"http://test.domain/I%C3%B1t%C3%ABrn%C3%A2ti%C3%B4n%EF%BF%BDliz%C3%A6ti%C3%B8n": b"http://test.domain/I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3\xb4n\xef\xbf\xbdliz\xc3\xa6ti\xc3\xb8n",
            # check that %20 in paths, params, query strings, and fragments are unescaped
            b'http://test.example/abcde%20def?que%20ry=str%20ing#frag%20ment': b'http://test.example/abcde def?que ry=str ing#frag ment',
            # check that spaces are collated to '+'
            b"http://test.example/path;par%20ams/with a%20space+/" : b"http://test.example/path;par ams/with a space+/",  # spaces in paths are ok
            b"http://[2001:db8:1f70::999:de8:7648:6e8]/test" : b"http://[2001:db8:1f70::999:de8:7648:6e8]/test", #ipv6 address
            b"http://[::ffff:192.168.1.1]/test" : b"http://[::ffff:192.168.1.1]/test", # ipv4 address in ipv6 notation
            b"http://[::ffff:192.168.1.1]:80/test" : b"http://[::ffff:192.168.1.1]/test", # ipv4 address in ipv6 notation
            b"htTps://[::fFff:192.168.1.1]:443/test" : b"https://[::ffff:192.168.1.1]/test", # ipv4 address in ipv6 notation

            # python 2.5 urlparse doesn't handle unknown protocols, so skipping this for now
            #"itms://itunes.apple.com/us/app/touch-pets-cats/id379475816?mt=8#23161525,,1293732683083,260430,tw" : "itms://itunes.apple.com/us/app/touch-pets-cats/id379475816?mt=8#23161525,,1293732683083,260430,tw", #can handle itms://

        }
        for bad, good in tests.items():
            metafunc.addcall(funcargs=dict(bad=bad, good=good))
    
    elif metafunc.function == test_unquote:
        for bad, good, unsafe in (
            (b'%20', b' ', b''),
            (b'%3f', b'%3F', b'?'), # don't unquote it, but uppercase it
            (b'%E3%82%AD', u'\u30ad', b''),
            ):
            metafunc.addcall(funcargs=dict(bad=bad, good=good, unsafe=unsafe))
    
    elif metafunc.function in [test_invalid_urls]:
        for url in [
            b'http://http://www.exemple.com/', # invalid domain
            b'-',
            b'asdf',
            b'HTTP://4294967297/test', # one more than max ip > int
            b'http://[img]http://i790.photobucket.com/albums/yy185/zack-32009/jordan.jpg[/IMG]',
            ]:
            metafunc.addcall(funcargs=dict(url=url))
    elif metafunc.function == test_norm_path:
        tests = {
            b'/foo/bar/.':                    b'/foo/bar/',
            b'/foo/bar/./':                   b'/foo/bar/',
            b'/foo/bar/..':                   b'/foo/',
            b'/foo/bar/../':                  b'/foo/',
            b'/foo/bar/../baz':               b'/foo/baz',
            b'/foo/bar/../..':                b'/',
            b'/foo/bar/../../':               b'/',
            b'/foo/bar/../../baz':            b'/baz',
            b'/foo/bar/../../../baz':         b'/../baz',
            b'/foo/bar/../../../../baz':      b'/baz',
            b'/./foo':                        b'/foo',
            b'/../foo':                       b'/../foo',
            b'/foo.':                         b'/foo.',
            b'/.foo':                         b'/.foo',
            b'/foo..':                        b'/foo..',
            b'/..foo':                        b'/..foo',
            b'/./../foo':                     b'/../foo',
            b'/./foo/.':                      b'/foo/',
            b'/foo/./bar':                    b'/foo/bar',
            b'/foo/../bar':                   b'/bar',
            b'/foo//':                        b'/foo/',
            b'/foo///bar//':                  b'/foo/bar/',
        }
        for bad, good in tests.items():
            metafunc.addcall(funcargs=dict(bad=bad, good=good))

def test_invalid_urls(url):
    try:
        output = urlnorm.norm(url)
        print('%r' % output)
    except urlnorm.InvalidUrl:
        return
    assert 1 == 0, "this should have raised an InvalidUrl exception"

def test_unquote(bad, good, unsafe):
    output = urlnorm.unquote_safe(bad, unsafe)
    assert_py2_str_eq(output, good)

def test_norms(bad, good):
    new_url = urlnorm.norm(bad)
    assert_py2_str_eq(new_url, _unicode(good))

def test_norm_path(bad, good):
    output = urlnorm.norm_path(b"http", bad)
    assert_py2_str_eq(output, _unicode(good))
