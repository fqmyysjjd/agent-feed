"""Choice parsing helpers for CLI flags and prompts."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import TypeVar


T = TypeVar("T", bound=StrEnum)


def parse_choice_csv(
    raw: str | None,
    *,
    enum_type: type[T],
    default: tuple[T, ...],
    value_name: str,
    allow_none: bool,
) -> tuple[T, ...]:
    if raw is None or raw.strip() == "":
        return default

    tokens = [token.strip().lower() for token in raw.split(",") if token.strip()]
    if not tokens:
        return default
    by_value = {item.value: item for item in enum_type}
    unknown = sorted(set(tokens).difference(by_value).difference({"all", "none"}))
    if unknown:
        extras = ("all", "none") if allow_none else ("all",)
        allowed = ", ".join((*by_value.keys(), *extras))
        raise ValueError(f"unknown {value_name}: {', '.join(unknown)}. Allowed values: {allowed}.")

    if "all" in tokens:
        if len(set(tokens)) > 1:
            raise ValueError(f"{value_name} cannot combine all with other values")
        return tuple(enum_type)
    if "none" in tokens:
        if allow_none:
            if len(set(tokens)) > 1:
                raise ValueError(f"{value_name} cannot combine none with other values")
            return ()
        raise ValueError(f"{value_name} cannot be none")

    return tuple(dict.fromkeys(by_value[token] for token in tokens))


def values(items: Iterable[StrEnum]) -> tuple[str, ...]:
    return tuple(item.value for item in items)
