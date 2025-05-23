from __future__ import absolute_import, division, print_function

__metaclass__ = type

from dataclasses import dataclass, asdict


def model_diff(source: dataclass, destination: dataclass) -> dict:
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
    if source.__class__.__name__ != destination.__class__.__name__:
        raise ValueError(
            f"The models are not the same: {source.__class__.__name__} != {destination.__class__.__name__}"
        )

    diff = {}

    source_as_dict = asdict(source)
    destination_as_dict = asdict(destination)

    for key, value in source_as_dict.items():
        if destination_as_dict[key] != value:
            diff[key] = value

    return diff
