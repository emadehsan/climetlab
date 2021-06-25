# (C) Copyright 2020 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import logging
import os
import weakref
from importlib import import_module

from climetlab.core import Base
from climetlab.decorators import locked

LOG = logging.getLogger(__name__)


class Reader(Base):
    def __init__(self, source, path):
        self._source = weakref.ref(source)
        self.path = path

    @property
    def source(self):
        return self._source()

    def mutate(self):
        # Give a chance to `directory` or `zip` to change the reader
        return self

    def sel(self, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def multi_merge(cls, readers):
        return None

    def cache_file(self, *args, **kwargs):
        return self.source.cache_file(*args, **kwargs)


_READERS = {}


# TODO: Add plugins
@locked
def _readers():
    if not _READERS:
        here = os.path.dirname(__file__)
        for path in os.listdir(here):
            if path.endswith(".py") and path[0] not in ("_", "."):
                name, _ = os.path.splitext(path)
                try:
                    module = import_module(f".{name}", package=__name__)
                    if hasattr(module, "reader"):
                        _READERS[name] = module.reader
                except Exception:
                    LOG.exception("Error loading reader %s", name)
    return _READERS


def reader(source, path):

    if os.path.isdir(path):
        from .directory import DirectoryReader

        return DirectoryReader(source, path).mutate()

    with open(path, "rb") as f:
        magic = f.read(8)

    for name, r in _readers().items():
        reader = r(source, path, magic)
        if reader is not None:
            return reader.mutate()

    from .unknown import Unknown

    return Unknown(source, path, magic)
