from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from prompt_toolkit.keys import Keys

from agent_feed import prompts
from agent_feed.models import CHECKS, CLIENTS
from agent_feed.prompts import (
    ESC_KEY_TIMEOUT_SECONDS,
    make_escape_eager,
    prompt_checks,
    prompt_clients,
    prompt_clients_step,
    tune_escape_key,
)


class PromptWithEager:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, dict[str, Any]]] = []

    def register_kb(self, *keys: Any, **kwargs: Any) -> Any:  # noqa: ANN002
        self.calls.append((keys, kwargs))

        def decorator(func: Any) -> Any:
            return func

        return decorator


class PromptWithoutEager:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, dict[str, Any]]] = []
        self.application: Any = None

    def register_kb(self, *keys: Any, filter: bool = True) -> Any:  # noqa: ANN002
        self.calls.append((keys, {"filter": filter}))

        def decorator(func: Any) -> Any:
            return func

        return decorator


def test_make_escape_eager_uses_eager_when_supported() -> None:
    prompt = PromptWithEager()

    returned = make_escape_eager(prompt)

    assert returned is prompt
    assert prompt.calls == [((Keys.Escape,), {"eager": True})]


def test_make_escape_eager_falls_back_when_eager_is_unsupported() -> None:
    prompt = PromptWithoutEager()

    returned = make_escape_eager(prompt)

    assert returned is prompt
    assert prompt.calls == [((Keys.Escape,), {"filter": True})]


def test_tune_escape_key_sets_zero_timeout_and_registers_escape() -> None:
    prompt = PromptWithoutEager()
    application = SimpleNamespace(ttimeoutlen=1.0)
    prompt.application = application

    returned = tune_escape_key(prompt)

    assert returned is prompt
    assert application.ttimeoutlen == ESC_KEY_TIMEOUT_SECONDS
    assert prompt.calls == [((Keys.Escape,), {"filter": True})]


def test_tune_escape_key_without_register_kb_is_a_noop() -> None:
    prompt = SimpleNamespace(application=SimpleNamespace(ttimeoutlen=1.0))

    returned = tune_escape_key(prompt)

    assert returned is prompt
    assert prompt.application.ttimeoutlen == ESC_KEY_TIMEOUT_SECONDS


def test_checkbox_prompts_do_not_preselect_defaults(monkeypatch: Any) -> None:
    captured: list[dict[str, Any]] = []

    class CheckboxPrompt:
        def __init__(self, kwargs: dict[str, Any]) -> None:
            self.kwargs = kwargs
            self.application = SimpleNamespace(ttimeoutlen=1.0)

        def register_kb(self, *_keys: Any, **_kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                return func

            return decorator

        def execute(self) -> list[Any]:
            return []

    def checkbox(**kwargs: Any) -> CheckboxPrompt:
        captured.append(kwargs)
        return CheckboxPrompt(kwargs)

    monkeypatch.setattr(prompts, "inquirer", SimpleNamespace(checkbox=checkbox))

    assert prompt_clients(tuple(CLIENTS)) == ()
    assert prompt_clients_step(tuple(CLIENTS)) == ()
    assert prompt_checks(tuple(CHECKS)) == ()

    assert [call["default"] for call in captured] == [[], [], []]
