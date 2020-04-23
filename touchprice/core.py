from pydantic import BaseModel
import typing
from enum import Enum


class Base(BaseModel):
    @classmethod
    def _get_value(
        cls,
        v: typing.Any,
        to_dict: bool,
        by_alias: bool,
        include: typing.Optional[typing.Union["AbstractSetIntStr", "DictIntStrAny"]],
        exclude: typing.Optional[typing.Union["AbstractSetIntStr", "DictIntStrAny"]],
        exclude_unset: bool,
        exclude_defaults: bool,
        # exclude_none: bool,
    ) -> typing.Any:
        if to_dict and isinstance(v, Enum):
            return v.value
        return super()._get_value(
            v,
            to_dict,
            by_alias,
            include,
            exclude,
            exclude_unset,
            exclude_defaults,
            # exclude_none,
        )

    def _iter(
        self,
        to_dict: bool = False,
        by_alias: bool = False,
        allowed_keys: typing.Optional["SetStr"] = None,
        include: typing.Union["AbstractSetIntStr", "DictIntStrAny"] = None,
        exclude: typing.Union["AbstractSetIntStr", "DictIntStrAny"] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
    ) -> "TupleGenerator":

        value_exclude = ValueItems(self, exclude) if exclude else None
        value_include = ValueItems(self, include) if include else None

        if exclude_defaults:
            if allowed_keys is None:
                allowed_keys = set(self.__fields__)
            for k, v in self.__field_defaults__.items():
                if self.__dict__[k] == v:
                    allowed_keys.discard(k)

        for k, v in self.__dict__.items():
            if allowed_keys is None or k in allowed_keys:
                value = self._get_value(
                    v,
                    to_dict=to_dict,
                    by_alias=by_alias,
                    include=value_include and value_include.for_element(k),
                    exclude=value_exclude and value_exclude.for_element(k),
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    # exclude_none=exclude_none,
                )
                if not (exclude_none and value is None):
                    yield k, value
