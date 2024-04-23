from __future__ import annotations

import re
import sys
from types import TracebackType
from typing import Any

import pytest

import trio
from trio.testing import Matcher, RaisesGroup

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


def wrap_escape(s: str) -> str:
    return "^" + re.escape(s) + "$"


def test_raises_group() -> None:
    with pytest.raises(
        ValueError,
        match=wrap_escape(
            f'Invalid argument "{TypeError()!r}" must be exception type, Matcher, or RaisesGroup.'
        ),
    ):
        RaisesGroup(TypeError())

    with RaisesGroup(ValueError):
        raise ExceptionGroup("foo", (ValueError(),))

    with RaisesGroup(SyntaxError):
        with RaisesGroup(ValueError):
            raise ExceptionGroup("foo", (SyntaxError(),))

    # multiple exceptions
    with RaisesGroup(ValueError, SyntaxError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # order doesn't matter
    with RaisesGroup(SyntaxError, ValueError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # nested exceptions
    with RaisesGroup(RaisesGroup(ValueError)):
        raise ExceptionGroup("foo", (ExceptionGroup("bar", (ValueError(),)),))

    with RaisesGroup(
        SyntaxError,
        RaisesGroup(ValueError),
        RaisesGroup(RuntimeError),
    ):
        raise ExceptionGroup(
            "foo",
            (
                SyntaxError(),
                ExceptionGroup("bar", (ValueError(),)),
                ExceptionGroup("", (RuntimeError(),)),
            ),
        )

    # will error if there's excess exceptions
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError):
            raise ExceptionGroup("", (ValueError(), ValueError()))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError):
            raise ExceptionGroup("", (RuntimeError(), ValueError()))

    # will error if there's missing exceptions
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, ValueError):
            raise ExceptionGroup("", (ValueError(),))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, SyntaxError):
            raise ExceptionGroup("", (ValueError(),))


def test_flatten_subgroups() -> None:
    # loose semantics, as with expect*
    with RaisesGroup(ValueError, flatten_subgroups=True):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

    with RaisesGroup(ValueError, TypeError, flatten_subgroups=True):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(), TypeError())),))
    with RaisesGroup(ValueError, TypeError, flatten_subgroups=True):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()]), TypeError()])

    # mixed loose is possible if you want it to be at least N deep
    with RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))
    with RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)):
        raise ExceptionGroup(
            "", (ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),)),)
        )
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)):
            raise ExceptionGroup("", (ValueError(),))

    # but not the other way around
    with pytest.raises(
        ValueError,
        match="^You cannot specify a nested structure inside a RaisesGroup with",
    ):
        RaisesGroup(RaisesGroup(ValueError), flatten_subgroups=True)


def test_catch_unwrapped_exceptions() -> None:
    # Catches lone exceptions with strict=False
    # just as except* would
    with RaisesGroup(ValueError, allow_unwrapped=True):
        raise ValueError

    # expecting multiple unwrapped exceptions is not possible
    with pytest.raises(
        ValueError, match="^You cannot specify multiple exceptions with"
    ):
        with RaisesGroup(SyntaxError, ValueError, allow_unwrapped=True):
            ...
    # if users want one of several exception types they need to use a Matcher
    # (which the error message suggests)
    with RaisesGroup(
        Matcher(check=lambda e: isinstance(e, (SyntaxError, ValueError))),
        allow_unwrapped=True,
    ):
        raise ValueError

    # Unwrapped nested `RaisesGroup` is likely a user error, so we raise an error.
    with pytest.raises(ValueError, match="has no effect when expecting"):
        with RaisesGroup(RaisesGroup(ValueError), allow_unwrapped=True):
            ...
    # But it *can* be used to check for nesting level +- 1 if they move it to
    # the nested RaisesGroup. Users should probably use `Matcher`s instead though.
    with RaisesGroup(RaisesGroup(ValueError, allow_unwrapped=True)):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()])])
    with RaisesGroup(RaisesGroup(ValueError, allow_unwrapped=True)):
        raise ExceptionGroup("", [ValueError()])

    # with allow_unwrapped=False (default) it will not be caught
    with pytest.raises(ValueError, match="^value error text$"):
        with RaisesGroup(ValueError):
            raise ValueError("value error text")

    # code coverage
    with pytest.raises(TypeError):
        with RaisesGroup(ValueError, allow_unwrapped=True):
            raise TypeError


def test_match() -> None:
    # supports match string
    with RaisesGroup(ValueError, match="bar"):
        raise ExceptionGroup("bar", (ValueError(),))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, match="foo"):
            raise ExceptionGroup("bar", (ValueError(),))


def test_check() -> None:
    exc = ExceptionGroup("", (ValueError(),))
    with RaisesGroup(ValueError, check=lambda x: x is exc):
        raise exc
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, check=lambda x: x is exc):
            raise ExceptionGroup("", (ValueError(),))


def test_RaisesGroup_matches() -> None:
    rg = RaisesGroup(ValueError)
    assert not rg.matches(None)
    assert not rg.matches(ValueError())
    assert rg.matches(ExceptionGroup("", (ValueError(),)))


def test_message() -> None:
    def check_message(message: str, body: RaisesGroup[Any]) -> None:
        with pytest.raises(
            AssertionError,
            match=f"^DID NOT RAISE any exception, expected {re.escape(message)}$",
        ):
            with body:
                ...

    # basic
    check_message("ExceptionGroup(ValueError)", RaisesGroup(ValueError))
    # multiple exceptions
    check_message(
        "ExceptionGroup(ValueError, ValueError)", RaisesGroup(ValueError, ValueError)
    )
    # nested
    check_message(
        "ExceptionGroup(ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(ValueError)),
    )

    # Matcher
    check_message(
        "ExceptionGroup(Matcher(ValueError, match='my_str'))",
        RaisesGroup(Matcher(ValueError, "my_str")),
    )
    check_message(
        "ExceptionGroup(Matcher(match='my_str'))",
        RaisesGroup(Matcher(match="my_str")),
    )

    # BaseExceptionGroup
    check_message(
        "BaseExceptionGroup(KeyboardInterrupt)", RaisesGroup(KeyboardInterrupt)
    )
    # BaseExceptionGroup with type inside Matcher
    check_message(
        "BaseExceptionGroup(Matcher(KeyboardInterrupt))",
        RaisesGroup(Matcher(KeyboardInterrupt)),
    )
    # Base-ness transfers to parent containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt)),
    )
    # but not to child containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt), ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt), RaisesGroup(ValueError)),
    )


def test_matcher() -> None:
    with pytest.raises(
        ValueError, match="^You must specify at least one parameter to match on.$"
    ):
        Matcher()  # type: ignore[call-overload]
    with pytest.raises(
        ValueError,
        match=f"^exception_type {re.escape(repr(object))} must be a subclass of BaseException$",
    ):
        Matcher(object)  # type: ignore[type-var]

    with RaisesGroup(Matcher(ValueError)):
        raise ExceptionGroup("", (ValueError(),))
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(TypeError)):
            raise ExceptionGroup("", (ValueError(),))


def test_matcher_match() -> None:
    with RaisesGroup(Matcher(ValueError, "foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(ValueError, "foo")):
            raise ExceptionGroup("", (ValueError("bar"),))

    # Can be used without specifying the type
    with RaisesGroup(Matcher(match="foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(match="foo")):
            raise ExceptionGroup("", (ValueError("bar"),))


def test_Matcher_check() -> None:
    def check_oserror_and_errno_is_5(e: BaseException) -> bool:
        return isinstance(e, OSError) and e.errno == 5

    with RaisesGroup(Matcher(check=check_oserror_and_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    # specifying exception_type narrows the parameter type to the callable
    def check_errno_is_5(e: OSError) -> bool:
        return e.errno == 5

    with RaisesGroup(Matcher(OSError, check=check_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(OSError, check=check_errno_is_5)):
            raise ExceptionGroup("", (OSError(6, ""),))


def test_matcher_tostring() -> None:
    assert str(Matcher(ValueError)) == "Matcher(ValueError)"
    assert str(Matcher(match="[a-z]")) == "Matcher(match='[a-z]')"
    pattern_no_flags = re.compile("noflag", 0)
    assert str(Matcher(match=pattern_no_flags)) == "Matcher(match='noflag')"
    pattern_flags = re.compile("noflag", re.IGNORECASE)
    assert str(Matcher(match=pattern_flags)) == f"Matcher(match={pattern_flags!r})"
    assert (
        str(Matcher(ValueError, match="re", check=bool))
        == f"Matcher(ValueError, match='re', check={bool!r})"
    )


def test__ExceptionInfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trio.testing._raises_group,
        "ExceptionInfo",
        trio.testing._raises_group._ExceptionInfo,
    )
    with trio.testing.RaisesGroup(ValueError) as excinfo:
        raise ExceptionGroup("", (ValueError("hello"),))
    assert excinfo.type is ExceptionGroup
    assert excinfo.value.exceptions[0].args == ("hello",)
    assert isinstance(excinfo.tb, TracebackType)


def test_deprecated_strict() -> None:
    """`strict` has been replaced with `flatten_subgroups`"""
    # parameter is typed as `None` to also emit a type error if passing anything
    with pytest.deprecated_call():
        RaisesGroup(ValueError, strict=False)  # type: ignore[arg-type]
    with pytest.deprecated_call():
        RaisesGroup(ValueError, strict=True)  # type: ignore[arg-type]
