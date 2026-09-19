import re

ROLE_LINE_PATTERN = re.compile(
    r"(священник|д[іi]акон|псаломщик|пономар)",
    re.IGNORECASE,
)
HEADER_SKIP_PATTERN = re.compile(
    r"(имя, отчество|мѣстожительство|совершил|поручителем|замѣтки|какомъ|месяцъ|день\.|числѣ)",
    re.IGNORECASE,
)
YEAR_IN_HEADER = re.compile(r"НА\s+(19\d{2}|190\[?\?\]|19\[?\?\])\s+ГОД", re.IGNORECASE)


def extract_role_lines(lines: list[str]) -> list[dict]:
    """Only lines with clergy/official titles and actual names — not column headers."""
    persons = []
    for line in lines:
        line_str = str(line).strip()
        if not line_str or HEADER_SKIP_PATTERN.search(line_str):
            continue
        match = ROLE_LINE_PATTERN.search(line_str)
        if not match:
            continue
        # Skip bare role words without a name (need text after the title)
        after_role = line_str[match.end() :].strip(" .:")
        if len(after_role) < 4:
            continue
        persons.append(
            {
                "full_name": line_str,
                "role": match.group(0),
                "location": None,
                "confidence": "medium",
                "source_fragment": line_str,
            }
        )
    return persons


def year_from_transcription(lines: list[str]) -> dict | None:
    for line in lines:
        line_str = str(line)
        match = YEAR_IN_HEADER.search(line_str)
        if not match:
            continue
        year_token = match.group(1)
        confidence = "low" if "[?" in year_token else "medium"
        return {
            "value": year_token.replace("[?]", "?"),
            "confidence": confidence,
            "source_fragment": line_str.strip(),
        }
    return None


def year_from_header_pass(header_result: dict | None) -> dict | None:
    if not header_result or not header_result.get("year"):
        return None
    year = str(header_result["year"])
    if not re.fullmatch(r"19\d{2}", year):
        return None
    if header_result.get("confidence") != "high":
        return None
    return {
        "value": year,
        "confidence": "high",
        "source_fragment": header_result.get("raw_fragment") or year,
    }


def resolve_header_year(lines: list[str], header_result: dict | None) -> dict | None:
    from_transcription = year_from_transcription(lines)
    from_header = year_from_header_pass(header_result)
    if from_header and from_transcription:
        if from_header["value"] == from_transcription["value"].replace("?", ""):
            from_header["confidence"] = "high"
            return from_header
        # Conflict — trust cautious transcription marker over header pass
        return from_transcription
    return from_transcription or from_header


def minimal_postprocess(result: dict) -> dict:
    lines = result.get("raw_transcription_lines") or []
    joined = "\n".join(str(line) for line in lines).lower()

    if not result.get("document_type") and "метрическ" in joined:
        if "бракосочет" in joined:
            result["document_type"] = "Метрическая книга о бракосочетавшихся"
        else:
            result["document_type"] = "Метрическая книга"
        result["document_type_confidence"] = "medium"

    resolved_year = resolve_header_year(lines, result.get("header_year"))
    result["header_year"] = resolved_year
    result["dates"] = [resolved_year] if resolved_year else []
    result["persons"] = extract_role_lines(lines)
    result["locations"] = []
    return result
