from __future__ import absolute_import, print_function, unicode_literals
__metaclass__ = type

import unittest

from restish import http, resource, templating


def _ensure_bytes(s):
    # In Python 2, str() and repr() return bytes object, since `str is bytes`,
    # but in Python 3, they return str objects (i.e. unicodes).  However, in
    # both versions, bytes objects must be returned as the body, so this
    # function is a helper to ensure that.  Assume utf-8.
    if isinstance(s, bytes):
        return s
    return s.encode('utf-8')

try:
    # Python 2
    unicode_type = unicode
except NameError:
    # Python 3
    unicode_type = str


class TestModule(unittest.TestCase):

    def test_exports(self):
        """
        Test that default rendering methods are available at module scope.
        """
        keys = dir(templating)
        assert 'render' in keys
        assert 'page' in keys
        assert 'element' in keys


class TestArgs(unittest.TestCase):

    def test_args(self):
        """
        Test that common rendering args are correct.
        """
        T = templating.Templating(None)
        request = http.Request.blank('/')
        args = T.args(request)
        assert set(['urls']) == set(args)

    def test_element_args(self):
        """
        Test that element rendering args are correct.
        """
        T = templating.Templating(None)
        request = http.Request.blank('/')
        args = T.element_args(request, None)
        assert set(['urls', 'element']) == set(args)

    def test_page_args(self):
        """
        Test that page rendering args are correct.
        """
        T = templating.Templating(None)
        request = http.Request.blank('/')
        args = T.page_args(request, None)
        assert set(['urls', 'element']) == set(args)

    def test_args_chaining(self):
        """
        Test that an extra common arg is also available to elements and pages.
        """
        class Templating(templating.Templating):
            def args(self, request):
                args = super(Templating, self).args(request)
                args['extra'] = None
                return args
        T = Templating(None)
        request = http.Request.blank('/')
        assert set(['urls', 'extra']) == set(T.args(request))
        assert set(['urls', 'element', 'extra']) == set(T.element_args(request, None))
        assert set(['urls', 'element', 'extra']) == set(T.element_args(request, None))

    def test_overloading(self):
        class Templating(templating.Templating):
            def render(self, request, template, args=None, encoding=None):
                return [_ensure_bytes(repr(args))]
            def args(self, request):
                args = super(Templating, self).args(request)
                args['extra_arg'] = None
                return args
            def element_args(self, request, element):
                args = super(Templating, self).element_args(request, element)
                args['extra_element_arg'] = None
                return args
            def page_args(self, request, page):
                args = super(Templating, self).page_args(request, page)
                args['extra_page_arg'] = None
                return args
        T = Templating(None)
        # Check that the overloaded args are all present.
        args = T.args(None)
        element_args = T.element_args(None, None)
        page_args = T.page_args(None, None)
        for t in [args, element_args, page_args]:
            assert 'extra_arg' in t
        for t in [element_args, page_args]:
            assert 'extra_element_arg' in t
        assert 'extra_page_arg' in page_args
        # Check that the args all get through to the render() method.
        @templating.page(None)
        def page(page, request):
            return {}
        @templating.element(None)
        def element(element, request):
            return {}
        request = http.Request.blank('/', environ={'restish.templating': T})
        for name in [b'extra_arg', b'extra_element_arg', b'extra_page_arg']:
            assert name in page(None, request).body
        elements = element(None, request)
        self.assertEqual(len(elements), 1)
        element_0 = elements[0]
        for name in [b'extra_arg', b'extra_element_arg']:
            assert name in element_0


class TestRendering(unittest.TestCase):

    def test_unconfigured(self):
        try:
            templating.Templating(None).render(http.Request.blank('/'),
                                               'foo.html')
        except TypeError as e:
            assert 'renderer' in unicode_type(e)

    def test_render(self):
        def renderer(template, args, encoding=None):
            printable_args = ', '.join("'%s'" % arg for arg in sorted(args))
            text = "%s [%s]" % (template, printable_args)
            # XXX We need to return bytes but encoding will be None.  Is it
            # appropriate to default to utf-8?
            return text.encode('utf-8' if encoding is None else encoding)
        request = http.Request.blank('/', environ={'restish.templating': templating.Templating(renderer)})
        self.assertEqual(templating.render(request, 'render'),
                         b"render ['urls']")

    def test_render_element(self):
        def renderer(template, args, encoding=None):
            printable_args = ', '.join("'%s'" % arg for arg in sorted(args))
            text = "%s [%s]" % (template, printable_args)
            # XXX We need to return bytes but encoding will be None.  Is it
            # appropriate to default to utf-8?
            return text.encode('utf-8' if encoding is None else encoding)
        request = http.Request.blank('/', environ={'restish.templating': templating.Templating(renderer)})
        self.assertEqual(templating.render_element(request, None, 'element'),
                         b"element ['element', 'urls']")

    def test_render_page(self):
        def renderer(template, args, encoding=None):
            printable_args = ', '.join("'%s'" % arg for arg in sorted(args))
            text = "%s [%s]" % (template, printable_args)
            return text.encode(encoding)
        request = http.Request.blank('/', environ={'restish.templating': templating.Templating(renderer)})
        self.assertEqual(templating.render_page(request, None, 'page'),
                         b"page ['element', 'urls']")

    def test_render_response(self):
        def renderer(template, args, encoding=None):
            printable_args = ', '.join("'%s'" % arg for arg in sorted(args))
            text = "%s [%s]" % (template, printable_args)
            return [text.encode(encoding)]
        request = http.Request.blank('/', environ={'restish.templating': templating.Templating(renderer)})
        response = templating.render_response(request, None, 'page')
        assert response.status == "200 OK"
        assert response.headers['Content-Type'] == 'text/html; charset=utf-8'
        self.assertEqual(response.body, "page ['element', 'urls']")

    def test_encoding(self):
        """
        Check that only a rendered page encoded output by default.
        """
        def renderer(template, args, encoding=None):
            return _ensure_bytes(str(encoding))
        @templating.element('element')
        def element(element, request):
            return {}
        @templating.page('page')
        def page(page, request):
            return {}
        request = http.Request.blank('/', environ={'restish.templating': templating.Templating(renderer)})
        assert templating.render(request, 'render') == 'None'
        assert element(None, request) == 'None'
        assert page(None, request).body == 'utf-8'


class TestPage(unittest.TestCase):

    def test_page_decorator(self):
        def renderer(template, args, encoding=None):
            args.pop('urls')
            args.pop('element')
            text = '<p>%s %r</p>' % (template, args)
            return [text.encode(encoding)]
        class Resource(resource.Resource):
            def __init__(self, args):
                self.args = args
            @resource.GET()
            @templating.page('test.html')
            def html(self, request):
                return self.args
        environ = {'restish.templating': templating.Templating(renderer)}
        request = http.Request.blank('/', environ=environ)
        response = Resource({})(request)
        assert response.status.startswith('200')
        self.assertEqual(response.body, b'<p>test.html {}</p>')
        response = Resource({b'foo': b'bar'})(request)
        assert response.status.startswith('200')
        self.assertEqual(response.body, '<p>test.html {\'foo\': \'bar\'}</p>')

    def test_page_decorator_with_custom_headers(self):
        def renderer(template, args, encoding=None):
            return args['body']

        class Resource(resource.Resource):
            @resource.GET()
            @templating.page('page')
            def get(self, request):
                # See this link for the following use case:
                # http://sites.google.com/a/snaplog.com/wiki/short_url
                return [('Link', '<http://sho.rt/1>; rel=shorturl'),
                        ('X-Foo', 'Bar')], \
                       {'body': [b'Hello World!']}

        environ = {'restish.templating': templating.Templating(renderer)}
        request = http.Request.blank('/', environ=environ)
        response = Resource()(request)
        assert response.status.startswith('200')
        assert response.body == b'Hello World!'
        assert response.headers.get('Link') == '<http://sho.rt/1>; rel=shorturl'
        assert response.headers.get('X-Foo') == 'Bar'


if __name__ == '__main__':
    unittest.main()

