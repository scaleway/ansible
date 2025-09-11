from __future__ import absolute_import, division, print_function

from dataclasses import asdict, dataclass, field
from typing import Type, TypeVar


T = TypeVar("T", bound="Model")


@dataclass
class Model:
    @classmethod
    def build_model(cls: Type[T], parameters: dict) -> T:
        model = cls(
            **{k: v for k, v in parameters.items() if k in cls.__dataclass_fields__}
        )
        return model

    def diff(self, other: "Model") -> dict:
        """
        diff two models guaranteed to be the same type
        the source model is the source of truth

        example:
            source:
                Secret(
                    key1="value1",
                    key2="value2",
                )
            destination:
                Secret(
                    key1="value1",
                    key2="value2",
                )
            return:
                {}

            source:
                Secret(
                    key1="value1",
                    key2="value2",
                )
            destination:
                Secret(
                    key1="value2",
                    key2="value3",
                )
            return:
                {
                    "key1": "value1",
                    "key2": "value2",
                }
        """
        if self.__class__.__name__ != other.__class__.__name__:
            raise ValueError(
                f"The models are not the same: {self.__class__.__name__} != {other.__class__.__name__}"
            )

        diff = {}

        self_as_dict = asdict(self)
        other_as_dict = asdict(other)

        for key, value in self_as_dict.items():
            if other_as_dict[key] != value:
                diff[key] = value

        return diff


@dataclass
class Secret(Model):
    name: str
    id: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class SecretVersion(Model):
    secret_id: str
    revision: str
    data: str = ""
    description: str = ""
