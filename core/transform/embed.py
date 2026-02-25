from __future__ import annotations

from typing import Any


def is_valid_url(value: str) -> bool:
    return isinstance(value, str) and value.strip().lower().startswith(("http://", "https://"))


def sanitize_embed(embed: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Sanitize and truncate embed fields to satisfy Discord validation rules."""
    changes: list[str] = []
    if not isinstance(embed, dict):
        return embed, ["embed_not_dict"]

    max_title = 256
    max_description = 4096
    max_fields = 25
    max_field_name = 256
    max_field_value = 1024
    max_embed_total = 6000

    for key in list(embed.keys()):
        if embed[key] in (None, ""):
            embed.pop(key, None)
            changes.append(f"removed_empty_{key}")

    if "title" in embed and isinstance(embed["title"], str) and len(embed["title"]) > max_title:
        embed["title"] = embed["title"][:max_title]
        changes.append("truncated_title")

    if "description" in embed and isinstance(embed["description"], str) and len(embed["description"]) > max_description:
        embed["description"] = embed["description"][:max_description]
        changes.append("truncated_description")

    if "author" in embed and isinstance(embed["author"], dict):
        if "icon_url" in embed["author"] and not is_valid_url(embed["author"]["icon_url"]):
            embed["author"].pop("icon_url", None)
            changes.append("removed_invalid_author_icon_url")

    if "footer" in embed and isinstance(embed["footer"], dict):
        if "icon_url" in embed["footer"] and not is_valid_url(embed["footer"]["icon_url"]):
            embed["footer"].pop("icon_url", None)
            changes.append("removed_invalid_footer_icon_url")

    if "image" in embed and isinstance(embed["image"], dict):
        if not is_valid_url(embed["image"].get("url", "")):
            embed.pop("image", None)
            changes.append("removed_invalid_image")

    if "thumbnail" in embed and isinstance(embed["thumbnail"], dict):
        if not is_valid_url(embed["thumbnail"].get("url", "")):
            embed.pop("thumbnail", None)
            changes.append("removed_invalid_thumbnail")

    if "fields" in embed and isinstance(embed["fields"], list):
        new_fields = []
        for field in embed["fields"]:
            if not isinstance(field, dict):
                continue
            name = field.get("name", "")
            value = field.get("value", "")
            if name == "" and value == "":
                continue

            if len(name) > max_field_name:
                field["name"] = name[:max_field_name]
                changes.append("truncated_field_name")
            if len(value) > max_field_value:
                field["value"] = value[:max_field_value]
                changes.append("truncated_field_value")
            new_fields.append(field)

        if len(new_fields) > max_fields:
            new_fields = new_fields[:max_fields]
            changes.append("trimmed_fields_count")
        embed["fields"] = new_fields

    def _embed_char_count(embed_dict: dict[str, Any]) -> int:
        payload = ""
        for key in ("title", "description"):
            if key in embed_dict and isinstance(embed_dict[key], str):
                payload += embed_dict[key]
        for field in embed_dict.get("fields", []):
            payload += str(field.get("name", "")) + str(field.get("value", ""))
        if "footer" in embed_dict and isinstance(embed_dict["footer"].get("text", ""), str):
            payload += embed_dict["footer"].get("text", "")
        if "author" in embed_dict and isinstance(embed_dict["author"].get("name", ""), str):
            payload += embed_dict["author"].get("name", "")
        return len(payload)

    total_chars = _embed_char_count(embed)
    if total_chars > max_embed_total and "description" in embed and isinstance(embed["description"], str):
        excess = total_chars - max_embed_total
        new_len = max(0, len(embed["description"]) - excess)
        embed["description"] = embed["description"][:new_len]
        changes.append("trimmed_description_for_total_limit")

    return embed, changes