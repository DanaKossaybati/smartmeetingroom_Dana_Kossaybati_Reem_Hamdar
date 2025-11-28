# Configuration file for Sphinx documentation builder

import os
import sys

# Add the services directory to Python path for autodoc to find modules
sys_path = os.path.abspath('../../services')
sys.path.insert(0, sys_path)

# Project information
project = 'Smart Meeting Room - Services API'
copyright = '2025, Dana Kossaybati & Reem Hamdar'
author = 'Dana Kossaybati & Reem Hamdar'
release = '1.0.0'

# Sphinx extensions for automatic documentation generation
extensions = [
    'sphinx.ext.autodoc',           # Auto-generate docs from docstrings
    'sphinx.ext.napoleon',          # Support for Google/NumPy style docstrings
    'sphinx.ext.viewcode',          # Add links to source code
    'sphinx.ext.intersphinx',       # Link to other Sphinx documentation
    'sphinx_rtd_theme',             # ReadTheDocs theme
]

# Autodoc settings for better documentation generation
autodoc_default_options = {
    'members': True,                # Document class members
    'member-order': 'bysource',     # Order members by source code
    'special-members': '__init__',  # Include __init__ methods
    'undoc-members': True,          # Include members without docstrings
    'show-inheritance': True,       # Show inheritance in class docs
}

# Napoleon extension settings (for Google/NumPy docstring support)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Theme configuration
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 3,
    'includehidden': True,
    'titles_only': False,
}

# Add any paths that contain custom static files
html_static_path = ['_static']

# Additional configuration
master_doc = 'index'
language = 'en'
exclude_patterns = ['_build', '**.ipynb_checkpoints']

# Highlighting
pygments_style = 'sphinx'

# Output options
html_show_sourcelink = True
html_show_sphinx = True
html_show_copyright = True
