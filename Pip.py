from __future__ import annotations

import functools
import sys
from pathlib import Path
from types import UnionType
from typing import get_args, get_type_hints


def _is_dispatch_type(value: object) -> bool:
    if isinstance(value, type):
        return True

    return isinstance(value, UnionType) and all(
        isinstance(member, type) for member in get_args(value)
    )


def _infer_dispatch_type(function: object) -> object | None:
    try:
        hints = get_type_hints(function)
    except Exception:
        hints = getattr(function, "__annotations__", {}) or {}

    for name, annotation in hints.items():
        if name == "return":
            continue
        return annotation if _is_dispatch_type(annotation) else None

    return None


def patch_singledispatch() -> None:
    original_singledispatch = functools.singledispatch

    def patched_singledispatch(function):
        dispatcher = original_singledispatch(function)
        original_register = dispatcher.register

        def register(cls, func=None):
            if func is None and not _is_dispatch_type(cls):
                dispatch_type = _infer_dispatch_type(cls)
                if dispatch_type is not None:
                    return original_register(dispatch_type, cls)

            return original_register(cls, func)

        dispatcher.register = register
        return dispatcher

    functools.singledispatch = patched_singledispatch


def patch_distlib_finder() -> None:
    from pip._vendor.distlib import DistlibException
    from pip._vendor.distlib import resources as distlib_resources

    original_finder = distlib_resources.finder

    def finder(package):
        try:
            return original_finder(package)
        except DistlibException as exc:
            if "Unable to locate finder" not in str(exc):
                raise

            if package not in sys.modules:
                __import__(package)

            module = sys.modules[package]
            if getattr(module, "__path__", None) is None:
                raise

            return distlib_resources.ResourceFinder(module)

    distlib_resources.finder = finder


def patch_wheel_supported() -> None:
    from pip._internal.models.wheel import Wheel

    def _supported_tag_strings(tags) -> list[str]:
        return [str(tag) for tag in tags]

    def supported(self, tags) -> bool:
        supported_tags = set(_supported_tag_strings(tags))
        return any(str(file_tag) in supported_tags for file_tag in self.file_tags)

    def support_index_min(self, tags) -> int:
        supported_tags = _supported_tag_strings(tags)
        file_tags = {str(file_tag) for file_tag in self.file_tags}

        for index, tag in enumerate(supported_tags):
            if tag in file_tags:
                return index

        raise ValueError()

    def find_most_preferred_tag(self, tags, tag_to_priority) -> int:
        priority_by_tag = {str(tag): priority for tag, priority in tag_to_priority.items()}
        return min(
            priority_by_tag[str(file_tag)]
            for file_tag in self.file_tags
            if str(file_tag) in priority_by_tag
        )

    Wheel.supported = supported
    Wheel.support_index_min = support_index_min
    Wheel.find_most_preferred_tag = find_most_preferred_tag


def patch_package_finder_cache() -> None:
    from pip._internal.index.package_finder import PackageFinder

    def _hashes_cache_key(hashes) -> tuple[tuple[str, tuple[str, ...]], ...] | None:
        if hashes is None:
            return None

        allowed = getattr(hashes, "_allowed", None)
        if allowed is None:
            return (("__hash__", (str(hash(hashes)),)),)

        return tuple(
            sorted((algorithm, tuple(digests)) for algorithm, digests in allowed.items())
        )

    def find_best_candidate(self, project_name, specifier=None, hashes=None):
        cache_key = (
            project_name,
            str(specifier or ""),
            _hashes_cache_key(hashes),
        )
        cached = self._best_candidates.get(cache_key)
        if cached is not None:
            return cached

        candidates = self.find_all_candidates(project_name)
        candidate_evaluator = self.make_candidate_evaluator(
            project_name=project_name,
            specifier=specifier,
            hashes=hashes,
        )
        result = candidate_evaluator.compute_best_candidate(candidates)
        self._best_candidates[cache_key] = result
        return result

    PackageFinder.find_best_candidate = find_best_candidate


def patch_pip_subprocess_runner() -> None:
    from pip._internal import build_env
    from pip._internal.utils import subprocess as pip_subprocess

    original_call_subprocess = pip_subprocess.call_subprocess

    def bundled_pip_executable() -> str:
        executable = Path(sys.executable).resolve()
        return str(executable if executable.name.lower() == "pip.exe" else executable.with_name("pip.exe"))

    def rewrite_runner_command(cmd):
        if len(cmd) < 2:
            return cmd

        runner = cmd[1]
        if not isinstance(runner, str) or not runner.endswith("__pip-runner__.py"):
            return cmd

        return [bundled_pip_executable(), *cmd[2:]]

    def call_subprocess(cmd, *args, **kwargs):
        return original_call_subprocess(rewrite_runner_command(cmd), *args, **kwargs)

    pip_subprocess.call_subprocess = call_subprocess
    build_env.call_subprocess = call_subprocess


def apply_pip_runtime_patches() -> None:
    patch_distlib_finder()
    patch_package_finder_cache()
    patch_pip_subprocess_runner()
    patch_wheel_supported()


def main(argv: list[str] | None = None) -> int:
    patch_singledispatch()

    apply_pip_runtime_patches()
    from pip._internal.cli.main import main as pip_main

    return pip_main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
