from __future__ import absolute_import, print_function, unicode_literals
__metaclass__ = type


from paste.script import templates


class RestishTemplate(templates.Template):
    """
    Configure the paster template
    """
    egg_plugins = ['Restish']
    summary = "Template for creating a basic Restish package"
    _template_dir = 'pastertemplate'

