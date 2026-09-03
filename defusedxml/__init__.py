# defusedxml (trimmed vendored copy)
#
# Copyright (c) 2013 by Christian Heimes <christian@python.org>
# Licensed to PSF under a Contributor Agreement.
# See https://www.python.org/psf/license for licensing details.
"""Defuse XML bomb denial of service vulnerabilities.

This is a trimmed copy of the defusedxml PyPI package
(https://github.com/tiran/defusedxml, version 0.7.1), vendored into
this plugin so it does not depend on defusedxml being separately
installed. Only the ElementTree replacement is kept, since that is
the only part this plugin uses (see ``defusedxml.ElementTree.fromstring``
in ElementTree.py); the upstream package's minidom/pulldom/sax/expat/
xmlrpc/lxml wrappers and its ``defuse_stdlib()`` monkey-patch helper
(which depends on those other wrappers) have been removed as unused.
See LICENSE in this directory for the original PSF license text.
"""

from .common import (
    DefusedXmlException,
    DTDForbidden,
    EntitiesForbidden,
    ExternalReferenceForbidden,
    NotSupportedError,
)

__version__ = "0.7.1"

__all__ = [
    "DefusedXmlException",
    "DTDForbidden",
    "EntitiesForbidden",
    "ExternalReferenceForbidden",
    "NotSupportedError",
]
