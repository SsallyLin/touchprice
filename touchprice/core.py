from IPython.display import display, DisplayHandle
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
        include: typing.Optional[
            typing.Union["AbstractSetIntStr", "DictIntStrAny"]
        ],
        exclude: typing.Optional[
            typing.Union["AbstractSetIntStr", "DictIntStrAny"]
        ],
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
        allowed_keys: typing.Optional['SetStr'] = None,
        include: typing.Union['AbstractSetIntStr', 'DictIntStrAny'] = None,
        exclude: typing.Union['AbstractSetIntStr', 'DictIntStrAny'] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
    ) -> 'TupleGenerator':

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


class Scope(str, Enum):
    init = "init"
    update = "update"
    append = "append"


class MetaContent(Base):
    scope: Scope = Scope.init
    height: typing.Union[str, int] = "600px"
    width: typing.Union[str, int] = "800px"


class BaseContent(Base):
    meta: MetaContent = MetaContent()
    option: typing.Dict[str, typing.Any]


class Dataset(Base):
    source: typing.Dict[str, list]


class BaseOption(Base):
    dataset: typing.List[Dataset]


class UpdateContent(BaseContent):
    meta: MetaContent = MetaContent(scope=Scope.append)
    option: BaseOption


class DisplayCore:
    def __init__(self, content: BaseContent):
        self._app: str = "application/vnd.yvis.v1+json"
        self.content: BaseContent = content
        self.display_handle: DisplayHandle = None
        if not self.display_handle:
            self.display(self.content)

    def display(self, content: BaseContent):
        self.display_handle = display(
            {self._app: content.dict()}, raw=True, display_id=True
        )

    @staticmethod
    def update_data(data: dict, update_data: dict):
        for key, value in data.items():
            if isinstance(value, list):
                update_data[key].append(*value)
            elif isinstance(value, dict):
                update_data[key] = update_data(value, update_data[key])
            else:
                update_data[key] = value

    def update(self, content: UpdateContent):
        # self.update_data(content.option.dict(), self.content.option)
        for idx, dataset in enumerate(content.option.dataset):
            for col, value in dataset.source.items():
                self.content.option["dataset"][idx]["source"][col].extend(value)
        self.display_update(content)

    def display_update(self, content: UpdateContent):
        self.display_handle.update({self._app: content.dict()}, raw=True)