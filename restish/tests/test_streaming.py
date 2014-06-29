import io
import os
import tempfile
import unittest
import webtest

from restish import app, http, resource
from six import binary_type, text_type

try:
    # Python 2
    import cStringIO
    import StringIO
except ImportError:
    # Python 3
    cStringIO = StringIO = None


_SCALARTYPE = (binary_type, text_type)


class Resource(resource.Resource):
    def __init__(self, body, charset=None):
        # WebTest does not like returning bytes or strings from the iterator,
        # however it does different checks in Python 2 and 3.  E.g. in Python
        # 3, it disallows bytes and str, but in Python 2 it only disallows str
        # (i.e. bytes), but should also disallow unicodes.  The solution is to
        # always return a list of length 1 of these types.
        self.body = [body] if isinstance(body, _SCALARTYPE) else body
        self.charset = charset

    def __call__(self, request):
        ctype = 'text/plain'
        if self.charset is not None:
            ctype += "; charset='{}'".format(self.charset)
        return http.ok([('Content-Type', ctype)], self.body)


class TestStreaming(unittest.TestCase):

    def test_string(self):
        R = webtest.TestApp(app.RestishApp(Resource('string'))).get('/')
        assert R.status.startswith('200')
        assert R.body == 'string'

    @unittest.skipIf(StringIO is None, 'Python 2 only')
    def test_stringio(self):
        R = webtest.TestApp(app.RestishApp(Resource(
            StringIO.StringIO('stringio')))).get('/')
        assert R.status.startswith('200')
        assert R.body == 'stringio'

    @unittest.skipIf(cStringIO is None, 'Python 2 only')
    def test_cstringio(self):
        R = webtest.TestApp(app.RestishApp(
            Resource(cStringIO.StringIO('cstringio')))).get('/')
        assert R.status.startswith('200')
        assert R.body == 'cstringio'

    def test_bytesio(self):
        R = webtest.TestApp(app.RestishApp(
            Resource(io.BytesIO(b'bytesio')))).get('/')
        assert R.status.startswith('200')
        assert R.body == b'bytesio'

    def test_file(self):
        class FileStreamer(object):
            def __init__(self, f):
                self.f = f
            def __iter__(self):
                return self
            def next(self):
                data = self.f.read(100)
                if data:
                    return data
                raise StopIteration()
            def close(self):
                self.f.close()
        (fd, filename) = tempfile.mkstemp()
        f = os.fdopen(fd, 'w')
        f.write('file')
        f.close()
        f = open(filename)
        R = webtest.TestApp(app.RestishApp(Resource(FileStreamer(f)))).get('/')
        assert R.status.startswith('200')
        assert R.body == 'file'
        assert f.closed
        os.remove(filename)
