"Research report prompt construction and LLM output validation."
import json
import re

from app.ai.context_builder.builder import build_context

REQUIRED_SECTIONS = [
    "executive_summary",
    "instrument_information",
    "market_context",
    "technical_interpretation",
    "market_regime_interpretation",
    "risk_interpretation",
    "positive_findings",
    "negative_findings",
    "data_limitations",
    "engine_results_used",
    "data_sources",
]

SYSTEM_PROMPT = (
    "You are a financial research assistant for the PIMS platform. You interpret "
    "deterministic quantitative engine results. You must NOT invent numbers: use only "
    "values present in the provided context. Distinguish verified quantitative results "
    "from interpretation. Never claim an instrument is guaranteed to increase in value. "
    "Never provide trade execution instructions. Disclose missing or unavailable data "
    "in the data_limitations section. Respond with a single JSON object, no markdown."
)


class OutputValidationError(ValueError):
    """LLM output missing required sections or not valid JSON."""


def extract_json(text: str) -> dict:
    """Parse a JSON object from the model output, tolerating code fences."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise OutputValidationError(f"model output is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise OutputValidationError("model output is not a JSON object")
    return parsed


def validate_report(report: dict) -> dict:
    missing = [s for s in REQUIRED_SECTIONS if s not in report]
    if missing:
        raise OutputValidationError(f"report missing required sections: {missing}")
    return report


def build_report_prompt(context: dict) -> str:
    instruction = (
        "Produce a JSON research report with exactly these keys:\n"
        + "\n".join(f"- {k}" for k in REQUIRED_SECTIONS)
        + "\n\npositive_findings and negative_findings must be JSON arrays of strings. "
        "data_sources must list the engine outputs and their timestamps from the context. "
        "engine_results_used must map each engine to its provided values. "
        "If an engine is NOT AVAILABLE or PENDING, say so explicitly in data_limitations."
    )
    return f"{instruction}\n\nANALYTICAL CONTEXT (JSON):\n{json.dumps(context, default=str)}"
