# Session State

This directory stores local JSON state files for long-running AI-assisted development sessions.

Session state preserves only active conclusions needed to continue the current conversation after context compression. It is not a transcript and not durable project documentation.

Session JSON files are ignored by git. Promote stable conclusions into `.agents/rules/`, `.agents/domain/`, `.agents/skills/`, or design documents instead of keeping them here permanently.
