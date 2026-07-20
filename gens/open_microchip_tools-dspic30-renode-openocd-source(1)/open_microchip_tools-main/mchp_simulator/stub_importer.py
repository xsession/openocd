from __future__ import annotations

import importlib.machinery
import importlib.abc
import importlib.util
import sys
import types
from dataclasses import dataclass
from typing import Optional


@dataclass
class _Stub:
    fullname: str

    def __repr__(self) -> str:
        return f"<Stub {self.fullname}>"


def _is_package_name(segment: str) -> bool:
    # Java package segments are typically lowercase.
    return bool(segment) and segment[0].islower()


def _make_stub_class(class_name: str, fullname: str):
    class _DynamicStub:
        __qualname__ = class_name

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(
                f"{fullname} is not implemented in the clean-room Python port"
            )

    _DynamicStub.__name__ = class_name
    return _DynamicStub


class SimulatorNamespaceStubLoader(importlib.abc.Loader):  # type: ignore[attr-defined]
    def __init__(self, fullname: str, is_package: bool):
        self.fullname = fullname
        self.is_package = is_package

    def create_module(self, spec):
        return None  # default module creation

    def exec_module(self, module):
        module.__dict__.setdefault("__all__", [])

        if self.is_package:
            module.__dict__["__path__"] = []
            return

        class_name = self.fullname.rsplit(".", 1)[-1]
        stub_cls = _make_stub_class(class_name, self.fullname)
        module.__dict__[class_name] = stub_cls
        module.__dict__["__all__"].append(class_name)


class SimulatorNamespaceStubFinder(importlib.abc.MetaPathFinder):  # type: ignore[attr-defined]
    def __init__(self, prefix: str):
        self.prefix = prefix

    def find_spec(self, fullname: str, path, target=None):
        if fullname == self.prefix or not fullname.startswith(self.prefix + "."):
            return None

        # Prefer real modules/packages when they exist.
        if importlib.machinery.PathFinder.find_spec(fullname, path) is not None:
            return None

        last = fullname.rsplit(".", 1)[-1]
        is_pkg = _is_package_name(last)
        loader = SimulatorNamespaceStubLoader(fullname, is_package=is_pkg)
        spec = importlib.util.spec_from_loader(fullname, loader, is_package=is_pkg)
        if spec is not None and is_pkg:
            spec.submodule_search_locations = []
        return spec


_installed = False


def install(prefix: str) -> None:
    global _installed
    if _installed:
        return

    sys.meta_path.insert(0, SimulatorNamespaceStubFinder(prefix))
    _installed = True


__all__ = ["install"]
