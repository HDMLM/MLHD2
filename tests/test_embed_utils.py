from core.transform.embed import sanitize_embed


def test_sanitize_embed_truncates_and_removes_invalid_urls():
    embed = {
        "title": "T" * 300,
        "description": "D" * 5000,
        "author": {"name": "name", "icon_url": "not-a-url"},
        "footer": {"text": "f", "icon_url": "ftp://bad"},
        "thumbnail": {"url": "bad"},
        "image": {"url": "bad"},
        "fields": [{"name": "N" * 300, "value": "V" * 1200}],
    }

    sanitized, changes = sanitize_embed(embed)

    assert len(sanitized["title"]) == 256
    assert len(sanitized["description"]) == 4096
    assert "icon_url" not in sanitized["author"]
    assert "icon_url" not in sanitized["footer"]
    assert "thumbnail" not in sanitized
    assert "image" not in sanitized
    assert len(sanitized["fields"][0]["name"]) == 256
    assert len(sanitized["fields"][0]["value"]) == 1024
    assert "truncated_title" in changes
    assert "truncated_description" in changes


def test_sanitize_embed_enforces_total_char_limit():
    embed = {
        "title": "a" * 256,
        "description": "b" * 4096,
        "fields": [{"name": "c" * 256, "value": "d" * 1024}] * 3,
    }

    sanitized, changes = sanitize_embed(embed)

    total = (
        len(sanitized["title"])
        + len(sanitized["description"])
        + sum(len(f["name"]) + len(f["value"]) for f in sanitized["fields"])
    )
    assert total <= 6000
    assert "trimmed_description_for_total_limit" in changes
