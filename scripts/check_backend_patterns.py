from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_DIR = ROOT / "siop" / "view"

VIEW_DEF_RE = re.compile(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.MULTILINE)
LOGIN_REQUIRED_RE = re.compile(r"@login_required")
JSONRESPONSE_RE = re.compile(r"\bJsonResponse\b")
REQUEST_BODY_RE = re.compile(r"\brequest\.body\b")
SERVICE_ERROR_RE = re.compile(r"except\s+ServiceError\b")
JSON_FUNCTION_HINT_RE = re.compile(r"def\s+[a-zA-Z][a-zA-Z0-9_]*_(?:list|view|new|edit)\s*\(")
API_HELPER_HINT_RE = re.compile(r"\b(api_success|api_error|parse_json_body)\b")

MAX_LINES_WARNING = 700


def should_check_function(name: str) -> bool:
    prefixes = (
        "ocorrencia",
        "acesso",
        "manejo",
        "atendimento",
        "controle_bc",
    )
    return name.startswith(prefixes) or name in prefixes


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    line_count = len(text.splitlines())
    if line_count > MAX_LINES_WARNING:
        warnings.append(f"{path}: arquivo grande ({line_count} linhas)")

    has_json_related_functions = bool(JSON_FUNCTION_HINT_RE.search(text))
    uses_api_helpers = bool(API_HELPER_HINT_RE.search(text))

    if has_json_related_functions and not uses_api_helpers:
        errors.append(f"{path}: arquivo com endpoints de dominio sem uso de api_success/api_error/parse_json_body")

    if JSONRESPONSE_RE.search(text):
        errors.append(f"{path}: uso direto de JsonResponse fora de core/api.py")

    if REQUEST_BODY_RE.search(text) and "parse_json_body(" not in text:
        errors.append(f"{path}: uso direto de request.body sem parse_json_body")

    if "parse_json_body(" in text and not SERVICE_ERROR_RE.search(text):
        errors.append(f"{path}: parse_json_body usado sem tratamento de ServiceError")

    for match in VIEW_DEF_RE.finditer(text):
        name = match.group(1)
        if not should_check_function(name):
            continue

        prefix = text[: match.start()]
        last_lines = "\n".join(prefix.splitlines()[-4:])
        if not LOGIN_REQUIRED_RE.search(last_lines):
            errors.append(f"{path}: função '{name}' sem @login_required próximo da definição")

    return errors + [f"WARNING: {warning}" for warning in warnings]


def main() -> int:
    errors: list[str] = []

    for path in sorted(VIEW_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        errors.extend(check_file(path))

    hard_errors = [error for error in errors if not error.startswith("WARNING:")]
    warnings = [error for error in errors if error.startswith("WARNING:")]

    if hard_errors or warnings:
        print("Falhas de padrao backend encontradas:\n")
        for error in hard_errors + warnings:
            print(f"- {error}")
        return 1 if hard_errors else 0

    print("Padrao backend: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
