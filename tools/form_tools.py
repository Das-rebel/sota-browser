"""
SOTA Browser MCP Server — Form Engine Tools

Wraps form_engine.py API (ResumeParser, FormScanner, FormFiller).
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_parse_resume",
        "description": (
            "Parse plain-text resume into structured profile data "
            "(name, email, phone, education, experience, skills, etc). "
            "Use this to extract profile data before filling forms."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "resume_text": {"type": "string", "description": "Plain-text resume content"},
            },
            "required": ["resume_text"],
        },
    },
    {
        "name": "browser_analyze_form",
        "description": (
            "Analyze the current page's form structure. Detects Google Forms, "
            "standard HTML, Material UI, Ant Design, Bootstrap forms. Returns "
            "field types, labels, options, required status, and submit/navigation buttons."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_fill_form",
        "description": (
            "Fill form fields on the page using structured profile data. Auto-analyzes "
            "the form, matches fields to profile keys (first_name, email, phone, etc.), "
            "and fills them. Works with Google Forms, standard HTML, Material UI, etc."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "profile": {
                    "type": "object",
                    "description": "Profile data with keys like first_name, last_name, email, phone, city, state, etc.",
                },
                "skip_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Semantic field types to skip (e.g. ["salary", "gender"])',
                },
                "fill_unmatched": {
                    "type": "boolean",
                    "description": "Try to fill fields even without direct profile match",
                },
            },
            "required": ["tab_id", "profile"],
        },
    },
    {
        "name": "browser_fill_form_from_resume",
        "description": (
            "Parse a resume AND fill form fields in one shot. Pass raw resume text, "
            "it will be parsed into a profile and used to auto-fill all matching form fields."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "resume_text": {"type": "string", "description": "Plain-text resume content"},
                "skip_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Semantic field types to skip",
                },
                "fill_unmatched": {
                    "type": "boolean",
                    "description": "Try to fill fields even without direct profile match",
                },
            },
            "required": ["tab_id", "resume_text"],
        },
    },
    {
        "name": "browser_fill_form_page",
        "description": (
            "Fill current page of a multi-page form and click Next to advance. "
            "Use for Google Forms with multiple pages/sections."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "profile": {"type": "object", "description": "Profile data"},
                "skip_types": {"type": "array", "items": {"type": "string"}},
                "fill_unmatched": {"type": "boolean"},
            },
            "required": ["tab_id", "profile"],
        },
    },
    {
        "name": "browser_submit_form",
        "description": (
            "Submit the current form by finding and clicking the Submit button. "
            "Auto-detects the submit button from form analysis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_parse_resume(**kwargs):
        return await manager.parse_resume(kwargs["resume_text"])
    handlers["browser_parse_resume"] = browser_parse_resume

    async def browser_analyze_form(**kwargs):
        return await manager.analyze_form(kwargs["tab_id"])
    handlers["browser_analyze_form"] = browser_analyze_form

    async def browser_fill_form(**kwargs):
        return await manager.fill_form(
            kwargs["tab_id"],
            kwargs["profile"],
            kwargs.get("skip_types"),
            kwargs.get("fill_unmatched", False),
        )
    handlers["browser_fill_form"] = browser_fill_form

    async def browser_fill_form_from_resume(**kwargs):
        return await manager.fill_form_from_resume(
            kwargs["tab_id"],
            kwargs["resume_text"],
            kwargs.get("skip_types"),
            kwargs.get("fill_unmatched", False),
        )
    handlers["browser_fill_form_from_resume"] = browser_fill_form_from_resume

    async def browser_fill_form_page(**kwargs):
        return await manager.fill_form_page(
            kwargs["tab_id"],
            kwargs["profile"],
            kwargs.get("skip_types"),
            kwargs.get("fill_unmatched", False),
        )
    handlers["browser_fill_form_page"] = browser_fill_form_page

    async def browser_submit_form(**kwargs):
        return await manager.submit_form(kwargs["tab_id"])
    handlers["browser_submit_form"] = browser_submit_form

    return handlers
