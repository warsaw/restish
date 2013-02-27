from __future__ import absolute_import, print_function, unicode_literals
__metaclass__ = type

try:
    # Python 2
    import cStringIO
    import StringIO
except ImportError:
    # Python 3
    cStringIO = StringIO = None

from io import BytesIO
import os
import tempfile
import unittest
import webtest

from restish import app, http, resource

if str is bytes:
    # Python 2
    _scalartypes = (bytes, unicode)
else:
    # Python 3
    _scalartypes = (bytes, str)


class Resource(resource.Resource):
    def __init__(self, body):
        # webtest does not like returning bytes or strings from the iterator,
        # however it does different checks in Python 2 and 3.  E.g. in Python
        # 3, it disallows bytes and str, but in Python 2, it only disallows
        # str, i.e. bytes, but should also disallow unicodes.
        self.body = [body] if isinstance(body, _scalartypes) else body
    def __call__(self, request):
        return http.ok([('Content-Type', 'text/plain')], self.body)


class TestStreaming(unittest.TestCase):

    def test_string(self):
        resource = Resource(b'string')
        rapp = app.RestishApp(resource)
        t = webtest.TestApp(rapp)
        R = t.get('/')
        R = webtest.TestApp(app.RestishApp(Resource(b'string'))).get('/')
        assert R.status.startswith('200')
        self.assertEqual(R.body, b'string')

    @unittest.skipIf(StringIO is None, 'Python 3 has no StringIO')
    def test_stringio(self):
        R = webtest.TestApp(app.RestishApp(Resource(StringIO.StringIO(b'stringio')))).get('/')
        assert R.status.startswith('200')
        assert R.body == 'stringio'

    @unittest.skipIf(cStringIO is None, 'Python 3 has no cStringIO')
    def test_cstringio(self):
        R = webtest.TestApp(app.RestishApp(Resource(cStringIO.StringIO(b'cstringio')))).get('/')
        assert R.status.startswith('200')
        assert R.body == 'cstringio'

    def test_bytesio(self):
        R = webtest.TestApp(app.RestishApp(Resource(BytesIO(b'bytesio')))).get('/')
        assert R.status.startswith('200')
        self.assertEqual(R.body, b'bytesio')

    def test_file(self):
        class FileStreamer:
            def __init__(self, f):
                self.f = f
            def __iter__(self):
                return self
            def next(self):
                data = self.f.read(100)
                if data:
                    return data
                raise StopIteration()
            __next__ = next
            def close(self):
                self.f.close()
        (fd, filename) = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(b'file')
            with open(filename, 'rb') as f:
                resource = Resource(FileStreamer(f))
                test_app = webtest.TestApp(app.RestishApp(resource))
                R = test_app.get('/')
            assert R.status.startswith('200')
            self.assertEqual(R.body, b'file')
        finally:
            os.remove(filename)
