"""Tiny compatibility shim for librosa on modern Python versions.

Murmur uses ``parakeet-mlx``, which imports ``librosa`` to build mel filter
banks. Current ``librosa`` releases still declare ``numba`` as a hard
dependency, but Murmur's startup path only needs decorator symbols such as
``jit`` to exist at import time.

This shim provides no-op decorator implementations so the app can run without
the legacy ``numba``/``llvmlite`` toolchain.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])

__version__ = "0.0"


def _passthrough_decorator(*args: Any, **kwargs: Any):
    """Return a decorator that leaves the wrapped function unchanged."""

    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return args[0]

    def decorator(func: F) -> F:
        return func

    return decorator


@overload
def jit(func: F, /) -> F: ...


@overload
def jit(*args: Any, **kwargs: Any): ...


def jit(*args: Any, **kwargs: Any):
    return _passthrough_decorator(*args, **kwargs)


def njit(*args: Any, **kwargs: Any):
    return _passthrough_decorator(*args, **kwargs)


def guvectorize(*args: Any, **kwargs: Any):
    return _passthrough_decorator(*args, **kwargs)


def vectorize(*args: Any, **kwargs: Any):
    return _passthrough_decorator(*args, **kwargs)


def stencil(*args: Any, **kwargs: Any):
    return _passthrough_decorator(*args, **kwargs)


def prange(*args: int):
    return range(*args)
