# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#
import logging

from climetlab.arguments.transformers import (
    AliasTransformer,
    CanonicalTransformer,
    FormatTransformer,
    MultipleTransformer,
    TypeTransformer,
)

LOG = logging.getLogger(__name__)


def check_consistency(values1, values2):
    if isinstance(values1, (list, tuple)) and isinstance(values2, (list, tuple)):
        for x in values1:
            if x not in values2:
                raise ValueError(f"'{x}' is not in {values2}")


class Argument:
    def __init__(
        self,
        name,
        decorators,
    ):
        if name is not None:
            assert isinstance(name, str), name
        self.name = name
        self.decorators = decorators
        self._cmltype = None

    @property
    def cmltype(self):
        if self._cmltype:
            return self._cmltype

        type1 = None
        type2 = None

        if self.norm_deco:
            type1 = self.norm_deco.get_cml_type()

        if self.av_deco:
            type2 = self.av_deco.get_cml_type(self.name)

        if type1 and type2:
            assert type1 == type2
        else:
            if type1:
                type = type1
            else:
                type = type2

        if type:
            self._cmltype = type

        return self._cmltype

    def add_alias_transformers(self, pipeline):
        aliases = dict()
        _all = None
        for decorator in self.decorators:
            a = decorator.get_aliases()
            if a is None:
                continue
            if not aliases:
                aliases = a
                multiple = decorator.get_multiple()
                if multiple:
                    _all = decorator.get_values(self.name)
                continue
            if isinstance(aliases, dict) and isinstance(a, dict):
                aliases.update(a)
                continue
            raise ValueError(f"Cannot merge aliases {a} and {aliases}.")

        if aliases:
            pipeline.append(AliasTransformer(self.name, aliases, _all))

    @property
    def norm_deco(self):
        decos = [d for d in self.decorators if not d.is_availability]
        if decos:
            assert len(decos) == 1, decos
            return decos[0]
        return None

    @property
    def av_deco(self):
        decos = [d for d in self.decorators if d.is_availability]
        if decos:
            assert len(decos) == 1, decos
            return decos[0]
        return None

    def add_type_transformers(self, pipeline):
        if self.cmltype:
            pipeline.append(TypeTransformer(self.name, self.cmltype))

    def add_canonicalize_transformers(self, pipeline):
        values = None
        if self.norm_deco and not self.av_deco:
            values = self.norm_deco.get_values(self.name)

        if not self.norm_deco and self.av_deco:
            values = self.norm_av.get_values()

        if self.norm_deco and self.av_deco:
            values1 = self.norm_deco.get_values()
            values2 = self.norm_av.get_values()

            def merge_values(value1, value2):
                if values1 and values2:
                    check_consistency(values1, values2)
                    return values1
                if values1:
                    return value1
                if values2:
                    return value2
                return None

            values = merge_values(values1, values2)

        if values or self.cmltype:
            pipeline.append(
                CanonicalTransformer(
                    self.name,
                    values,
                    type=self.cmltype,
                )
            )

    def add_format_transformers(self, pipeline):
        if self.cmltype is not None:
            pipeline.append(
                FormatTransformer(
                    self.name,
                    type=self.cmltype,
                )
            )

    def add_multiple_transformers(self, pipeline):
        multiple = None
        for decorator in self.decorators:
            a = decorator.get_multiple()
            # assert a not incompatible with multiples
            if a is not None:
                multiple = a

        if multiple is not None:
            pipeline.append(MultipleTransformer(self.name, multiple))
