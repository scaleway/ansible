import importlib
import inspect
from dataclasses import fields
from datetime import datetime
from enum import Enum
from inspect import Parameter, isclass
import pkgutil
from types import FunctionType, NoneType
from typing import (
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scaleway import ALL_REGIONS, WaitForOptions

import scaleway


class FieldTypeDescriptor:
    name: str
    choices: List[str]

    def __init__(self, field_type: type):
        self.name = "???"

        if get_origin(field_type) == Union:
            generic_args = get_args(field_type)
            field_type = generic_args[0]

        self.name = ""
        if field_type == str:
            self.name = "str"
        elif field_type == int:
            self.name = "int"
        elif field_type == bool:
            self.name = "bool"
        elif get_origin(field_type) is dict:
            self.name = "dict"
        elif get_origin(field_type) is list:
            self.name = "list"
        elif field_type == float:
            self.name = "float"
        elif field_type is datetime:
            self.name = "str"
        elif isclass(field_type):
            if issubclass(field_type, Enum):
                self.name = "str"
                self.choices = [str(choice) for choice in field_type]
            else:
                self.name = "dict"

        if self.name == "":
            raise Exception(f"Unknown type: {field_type}")


class FieldDescriptor:
    name: str
    type: FieldTypeDescriptor
    required: bool
    description: str

    def __init__(self, name: str, parameter: Parameter):
        self.name = name

        if isinstance(parameter, Parameter):
            self.type = FieldTypeDescriptor(parameter.annotation)
            self.required = parameter.default == inspect.Parameter.empty
        else:
            self.type = FieldTypeDescriptor(parameter)
            self.required = True

        self.description = ""

        if name == "region":
            self.type.choices = ALL_REGIONS


class MethodDescriptor:
    name: str
    request_fields: List[FieldDescriptor]
    response_fields: List[FieldDescriptor]

    def __init__(self, method: FunctionType):
        self.name = method.__name__
        self.request_fields: List[FieldDescriptor] = []
        self.response_fields: List[FieldDescriptor] = []

        signature = inspect.signature(method)
        for name, parameter in signature.parameters.items():
            if name == "self":
                continue

            if get_origin(parameter.annotation) is Union:
                first_arg = get_args(parameter.annotation)[0]
                if get_origin(first_arg) is WaitForOptions:
                    continue

            self.request_fields.append(FieldDescriptor(name, parameter))

        return_type = method.__annotations__["return"]
        if return_type != NoneType:
            origin = get_origin(return_type)
            if origin == list or origin == Union:
                return_type = get_args(return_type)[0]

            hints = get_type_hints(return_type)

            for field in fields(return_type):
                self.response_fields.append(
                    FieldDescriptor(field.name, hints[field.name])
                )

    @property
    def required_request_fields(self):
        return [field for field in self.request_fields if field.required]

    def has_request_field(self, name: str) -> bool:
        for field in self.request_fields:
            if field.name == name:
                return True

        return False

    def has_response_field(self, name: str) -> bool:
        for field in self.response_fields:
            if field.name == name:
                return True

        return False


class APIDescriptor:
    namespace: str
    group: str

    api_class: Type[object]

    name: str
    method_create: Optional[MethodDescriptor]
    method_get: Optional[MethodDescriptor]
    method_update: Optional[MethodDescriptor]
    method_delete: Optional[MethodDescriptor]
    method_list: Optional[MethodDescriptor]
    method_wait_for: Optional[MethodDescriptor]

    request_id_field: Optional[FieldDescriptor]
    response_id_field: Optional[FieldDescriptor]

    def __init__(
        self,
        api_class: Type[object],
        namespace: str,
        group: str,
        methods: List[MethodDescriptor],
    ):
        self.api_class = api_class
        self.namespace = namespace
        self.group = group
        self.name = f"{namespace}_{group}" if group != "" else namespace

        self.method_create = None
        self.method_get = None
        self.method_update = None
        self.method_delete = None
        self.method_list = None
        self.method_wait_for = None

        for method in methods:
            if method.name.startswith("create_"):
                self.method_create = method
            elif method.name.startswith("get_"):
                self.method_get = method
            elif method.name.startswith("update_"):
                self.method_update = method
            elif method.name.startswith("delete_"):
                self.method_delete = method
            elif method.name.startswith("list_"):
                self.method_list = method
            elif method.name.startswith("wait_for_"):
                self.method_wait_for = method

        self.request_id_field = None
        self.response_id_field = None

        method_with_id_field = (
            self.method_get or self.method_update or self.method_update
        )
        if method_with_id_field is None:
            raise Exception(f"Unable to find method with ID field for {self.name}")

        for field in method_with_id_field.request_fields:
            if f"{group}_id" in field.name:
                self.request_id_field = field
                break

        for field in method_with_id_field.response_fields:
            if f"id" in field.name:
                self.response_id_field = field
                break

        if self.request_id_field is None:
            if len(method_with_id_field.request_fields) == 0:
                raise Exception(
                    f"Unable to find request ID field for {self.name} (no request fields)"
                )

            self.request_id_field = method_with_id_field.request_fields[0]

        if self.response_id_field is None:
            if len(method_with_id_field.response_fields) == 0:
                raise Exception(
                    f"Unable to find response ID field for {self.name} (no response fields)"
                )

            self.response_id_field = method_with_id_field.response_fields[0]

    @property
    def class_import_path(self) -> str:
        return ".".join(self.api_class.__module__.split(".")[:-1])

    @property
    def class_name(self) -> str:
        return self.api_class.__name__


def get_api_descriptors(namespace: str, api_class: Type[object]) -> List[APIDescriptor]:
    apis: List[APIDescriptor] = []

    prefixes = ["create_", "get_", "update_", "delete_", "list_", "wait_for_"]

    groups: Dict[str, List[MethodDescriptor]] = {}

    for name, method in inspect.getmembers(api_class, predicate=inspect.isfunction):
        for prefix in prefixes:
            if not name.startswith(prefix):
                continue

            parts = name.split("_", 1)
            group = parts[1]

            if prefix == "list_":
                if not group.endswith("_all"):
                    continue

                group = group.removesuffix("s_all")

            try:
                method_descriptor = MethodDescriptor(method)

                if group not in groups:
                    groups[group] = []
                groups[group].append(method_descriptor)
            except Exception as e:
                print(f"Error processing method {name}: {e}")

    for group, methods in groups.items():
        try:
            api = APIDescriptor(api_class, namespace, group, methods)
            if (
                api.method_create is None
                or api.method_get is None
                or api.method_delete is None
            ):
                continue
            apis.append(api)
        except Exception as e:
            print(f"Error processing API {namespace}.{group}: {e}")

    return apis


def main() -> None:
    modules = pkgutil.iter_modules(scaleway.__path__)
    apis: Dict[str, Type[object]] = {}

    for _, product, _ in modules:
        module = importlib.import_module(f"scaleway.{product}")
        versions = pkgutil.iter_modules(module.__path__)

        for _, version, _ in versions:
            module = importlib.import_module(f"scaleway.{product}.{version}")

            for name, api in inspect.getmembers(module, isclass):
                if name.endswith("API"):
                    apis[f"{product}_{version}"] = api

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(),
        extensions=["jinja2.ext.loopcontrols"],
    )

    module_names: List[str] = []

    for name, api in apis.items():
        descriptors = get_api_descriptors(name, api)

        for descriptor in descriptors:
            module_code = env.get_template("module.py.jinja").render(api=descriptor)
            with open(f"plugins/modules/scaleway_{descriptor.name}.py", "w") as f:
                f.write(module_code)

            module_names.append(descriptor.name)

    with open(f"meta/runtime.yml", "w") as f:
        content = env.get_template("runtime.yml.jinja").render(module_names=module_names)
        f.write(content)

if __name__ == "__main__":
    main()
