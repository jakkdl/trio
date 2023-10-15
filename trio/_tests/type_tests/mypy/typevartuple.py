# mypy does not currently support checking code against TypeVarTuples, but will do so very soon, so this file is merely to give a notification in CI when it's released.
from typing import Any

from trio.lowlevel import start_guest_run


async def bar(intparam: int, strparam: str) -> str:
    return "test"


ignore: Any = ...

start_guest_run(
    bar,
    7,
    "hello",
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)
start_guest_run(
    bar,  # type: ignore[arg-type]
    "7",
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)
start_guest_run(
    # mypy incorrectly classifies this as an invalid function to pass
    bar,  # type: ignore[arg-type]
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)


async def with_default_values(intparam: int, strparam: str = "...") -> float:
    return 2.3


# specify the optional value
start_guest_run(
    with_default_values,
    7,
    "7",
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)

# not specifying the optional value gives an error on pyright, but not mypy
# see https://github.com/python/typing/issues/1231
# and https://github.com/microsoft/pyright/issues/3775
start_guest_run(
    with_default_values,
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)

start_guest_run(
    with_default_values,  # type: ignore[arg-type]
    "7",
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)


async def with_args(*args: int) -> None:
    ...


start_guest_run(
    with_args,
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)
start_guest_run(
    with_args,
    7,
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)
start_guest_run(
    with_args,  # type: ignore[arg-type]
    7,
    7,
    2.3,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)


async def with_keyword_args(intparam: int, *, kw_arg: float) -> None:
    ...


start_guest_run(
    # pyright andy mypy correctly disallows passing a function that requires a keyword argument
    with_keyword_args,  # type: ignore[arg-type]
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)


# optional keyword arg is okay though
async def with_optional_keyword_arg(intparam: int, *, kw_arg: float = 2.3) -> None:
    ...


start_guest_run(
    with_optional_keyword_arg,
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)
start_guest_run(
    with_optional_keyword_arg,  # type: ignore[arg-type]
    2.3,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)


# or kwargs
async def with_kwargs(intparam: int, **kwargs: float) -> None:
    ...


start_guest_run(
    with_kwargs,
    7,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)
start_guest_run(
    with_kwargs,  # type: ignore[arg-type]
    2.3,
    run_sync_soon_threadsafe=ignore,
    done_callback=ignore,
)
