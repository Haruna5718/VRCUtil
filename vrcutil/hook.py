from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


HOOK_FILES = {
    "install": "Install",
    "uninstall": "Uninstall",
}


def _normalize_hook_name(hook: str) -> str:
    normalized = str(hook or "").strip().lower()
    if normalized not in HOOK_FILES:
        raise ValueError(f"Unsupported module hook: {hook!r}")
    return normalized


def resolve_module_hook(module_path: str | Path, hook: str) -> Path | None:
    module_path = Path(module_path)
    hook_base = HOOK_FILES[_normalize_hook_name(hook)]

    for candidate in (
        module_path / f"{hook_base}.py",
        module_path / f"{hook_base}.pyc",
        module_path / f"{hook_base}.pyd",
    ):
        if candidate.is_file():
            return candidate
    return None


def has_module_hook(module_path: str | Path, hook: str) -> bool:
    return resolve_module_hook(module_path, hook) is not None


def _load_hook_module(entry: Path, hook: str) -> tuple[ModuleType, str]:
    hook_base = HOOK_FILES[_normalize_hook_name(hook)]
    if entry.suffix.lower() == ".pyd":
        module_name = hook_base
    else:
        digest = hashlib.sha1(str(entry.resolve()).encode("utf-8"), usedforsecurity=False).hexdigest()
        module_name = f"_vrcutil_{entry.parent.name}_{hook_base.lower()}_{digest}"

    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, entry)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create a hook spec for {entry}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module_name


def _resolve_hook_callable(module: ModuleType, hook: str):
    for candidate in (_normalize_hook_name(hook), "run", "main"):
        func = getattr(module, candidate, None)
        if callable(func):
            return func
    raise AttributeError(f"{HOOK_FILES[_normalize_hook_name(hook)]} hook has no callable entry point.")


def _call_hook(func, context: dict[str, Any]):
    signature = inspect.signature(func)
    accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
    if accepts_kwargs:
        return func(**context)

    supported = {
        name: value
        for name, value in context.items()
        if name in signature.parameters
    }
    return func(**supported)


def invoke_module_hook(module_path: str | Path, hook: str, **context):
    module_path = Path(module_path)
    entry = resolve_module_hook(module_path, hook)
    if entry is None:
        return None

    module, module_name = _load_hook_module(entry, hook)
    try:
        func = _resolve_hook_callable(module, hook)
        result = _call_hook(
            func,
            {
                "module_path": module_path,
                **context,
            },
        )
        if result is False:
            raise RuntimeError(f"{HOOK_FILES[_normalize_hook_name(hook)]} hook returned False.")
        return result
    finally:
        sys.modules.pop(module_name, None)
