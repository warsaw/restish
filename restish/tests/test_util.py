from __future__ import absolute_import, print_function, unicode_literals
__metaclass__ = type

import unittest
import webtest

from restish import app, http, util


def wsgi_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    # Convert the environ elements we're interested into bytes, since the body
    # wants to be a bytes object.  UTF-8 I guess.
    script_name = environ.get('SCRIPT_NAME', b'')
    path_info = environ.get('PATH_INFO', b'')
    # Python 3 bytes objects have no .format() method.
    return [b''.join(
        (b'SCRIPT_NAME: ', script_name, b', PATH_INFO: ', path_info))]


class TestWSGI(unittest.TestCase):

    def test_wsgi(self):
        request = http.Request.blank('/foo/bar',
                                     environ={'REQUEST_METHOD': 'GET'})
        response = util.wsgi(request, wsgi_app, ['foo', 'bar'])
        assert response.status == '200 OK'
        assert response.headers['Content-Type'] == 'text/plain'
        assert response.body == 'SCRIPT_NAME: , PATH_INFO: /foo/bar'
        response = util.wsgi(request, wsgi_app, [u'bar'])
        assert response.status == '200 OK'
        assert response.headers['Content-Type'] == 'text/plain'
        assert response.body == 'SCRIPT_NAME: /foo, PATH_INFO: /bar'

    def test_root_wsgi_resource(self):
        """
        Test a WSGIResource that is the root resource.
        """
        testapp = webtest.TestApp(app.RestishApp(util.WSGIResource(wsgi_app)))
        response = testapp.get(b'/foo/bar', status=200)
        assert response.headers['Content-Type'] == 'text/plain'
        assert response.body == 'SCRIPT_NAME: , PATH_INFO: /foo/bar'

    def test_child_wsgi_resource(self):
        """
        Test a WSGIResource that is a child of the root resource.
        """
        class Root(object):
            def resource_child(self, request, segments):
                return util.WSGIResource(wsgi_app), segments[1:]
        testapp = webtest.TestApp(app.RestishApp(Root()))
        response = testapp.get(b'/foo/bar', status=200)
        assert response.headers['Content-Type'] == 'text/plain'
        assert response.body == 'SCRIPT_NAME: /foo, PATH_INFO: /bar'

