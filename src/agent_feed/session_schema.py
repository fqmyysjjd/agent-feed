"""Render session-state schema from project-level Agent Feed settings."""

from __future__ import annotations

import json
from pathlib import Path

from agent_feed.project_settings import read_project_settings


def render_session_schema(root: Path) -> str:
    settings = read_project_settings(root)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "AI Development Session Handoff",
        "type": "object",
        "required": ["schema_version", "session", "current_task", "carry_forwards"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "session": {
                "type": "object",
                "required": ["id", "label", "updated_at"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "label": {"type": "string", "minLength": 1},
                    "updated_at": {"type": "string", "minLength": 1},
                    "thread_id": {
                        "type": "string",
                        "description": "Optional AI-client thread id when the environment exposes it.",
                    },
                    "title_history": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional known conversation titles or aliases.",
                    },
                },
            },
            "current_task": {
                "type": "object",
                "required": ["goal", "current_step", "stop_condition", "next_action"],
                "additionalProperties": False,
                "properties": {
                    "goal": {"type": "string", "minLength": 1},
                    "current_step": {"type": "string", "minLength": 1},
                    "stop_condition": {"type": "string", "minLength": 1},
                    "next_action": {"type": "string", "minLength": 1},
                },
            },
            "carry_forwards": {
                "type": "array",
                "maxItems": settings.session_state.max_carry_forwards,
                "items": {
                    "type": "object",
                    "required": [
                        "id",
                        "type",
                        "content",
                        "why_keep",
                        "expires_when",
                        "updated_at",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "type": {
                            "type": "string",
                            "enum": ["decision", "constraint", "blocker", "handoff"],
                        },
                        "content": {"type": "string", "minLength": 1},
                        "why_keep": {"type": "string", "minLength": 1},
                        "expires_when": {"type": "string", "minLength": 1},
                        "updated_at": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
