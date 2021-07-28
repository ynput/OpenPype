# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

'''ftrack Python API documentation build configuration file.'''

import os
import re

# -- General ------------------------------------------------------------------

# Extensions.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'lowdown'
]


# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ftrack Python API'
copyright = u'2014, ftrack'

# Version
with open(
    os.path.join(
        os.path.dirname(__file__), '..', 'source',
        'ftrack_api', '_version.py'
    )
) as _version_file:
    _version = re.match(
        r'.*__version__ = \'(.*?)\'', _version_file.read(), re.DOTALL
    ).group(1)

version = _version
release = _version

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_template']

# A list of prefixes to ignore for module listings.
modindex_common_prefix = [
    'ftrack_api.'
]

# -- HTML output --------------------------------------------------------------

if not os.environ.get('READTHEDOCS', None) == 'True':
    # Only import and set the theme if building locally.
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['_static']
html_style = 'ftrack.css'

# If True, copy source rst files to output for reference.
html_copy_source = True


# -- Autodoc ------------------------------------------------------------------

autodoc_default_flags = ['members', 'undoc-members', 'inherited-members']
autodoc_member_order = 'bysource'


def autodoc_skip(app, what, name, obj, skip, options):
    '''Don't skip __init__ method for autodoc.'''
    if name == '__init__':
        return False

    return skip


# -- Intersphinx --------------------------------------------------------------

intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
    'ftrack': (
        'http://rtd.ftrack.com/docs/ftrack/en/stable/', None
    )
}


# -- Todos ---------------------------------------------------------------------

todo_include_todos = os.environ.get('FTRACK_DOC_INCLUDE_TODOS', False) == 'True'


# -- Setup --------------------------------------------------------------------

def setup(app):
    app.connect('autodoc-skip-member', autodoc_skip)
