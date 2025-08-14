# Sphinx configuration file for UW-Automation-Program
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'UW-Automation-Program'
copyright = '2025, Damion Morrison, Ben Dillon'
author = 'Damion Morrison, Ben Dillon'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'alabaster'
