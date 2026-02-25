from __future__ import annotations

import re
from typing import List


def parse_version(version: str) -> List[int]:
    if not version:
        return []
    value = version.strip()
    if value.startswith(("v", "V")):
        value = value[1:]
    parts: List[int] = []
    for segment in value.split("."):
        segment = segment.strip()
        if not segment:
            parts.append(0)
            continue
        numeric = ""
        for ch in segment:
            if ch.isdigit():
                numeric += ch
            else:
                break
        parts.append(int(numeric) if numeric else 0)
    while parts and parts[-1] == 0:
        parts.pop()
    return parts


def compare_versions(left: str, right: str) -> int:
    left_parts = parse_version(left)
    right_parts = parse_version(right)
    max_len = max(len(left_parts), len(right_parts))
    for index in range(max_len):
        left_value = left_parts[index] if index < len(left_parts) else 0
        right_value = right_parts[index] if index < len(right_parts) else 0
        if left_value > right_value:
            return 1
        if left_value < right_value:
            return -1
    return 0


def canon_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def format_update_summary(raw_result: str) -> str:
    result = raw_result or ""
    first_line = result.splitlines()[0] if result else ""
    if first_line.startswith("Safe ZIP Update"):
        if "Errors:" in result:
            return "Update Status: Partial Success\n" + result
        return "Update Status: Success\n" + result
    if "failed" in first_line.lower() or first_line.lower().startswith("could not"):
        return "Update Status: Failed\n" + result
    return "Update Status: Complete\n" + result
