"""Tests for the lightweight numba compatibility shim."""

from __future__ import annotations


def test_jit_returns_function_unchanged():
    import numba

    @numba.jit(nopython=True, cache=True)
    def add_one(value: int) -> int:
        return value + 1

    assert add_one(1) == 2


def test_guvectorize_returns_function_unchanged():
    import numba

    @numba.guvectorize(["void(float32[:], float32[:])"], "(n)->(n)")
    def passthrough(values, out):
        out[:] = values

    source = [1, 2, 3]
    target = [0, 0, 0]
    passthrough(source, target)
    assert target == source


def test_prange_delegates_to_range():
    import numba

    assert list(numba.prange(3)) == [0, 1, 2]
