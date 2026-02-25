from core.installer_utils import canon_name, compare_versions, format_update_summary, parse_version


def test_parse_version_handles_prefix_and_suffix() -> None:
    assert parse_version("v1.2.3") == [1, 2, 3]
    assert parse_version("2.4.0-beta") == [2, 4]


def test_compare_versions_semantic_numeric() -> None:
    assert compare_versions("1.2.10", "1.2.3") == 1
    assert compare_versions("1.0.0", "1") == 0
    assert compare_versions("0.9", "1.0") == -1


def test_canon_name_pep503() -> None:
    assert canon_name("My_Package.Name") == "my-package-name"


def test_format_update_summary_success() -> None:
    raw = "Safe ZIP Update to v1.2.3\nCreated: 1\nUpdated: 2"
    assert format_update_summary(raw).startswith("Update Status: Success")


def test_format_update_summary_failed() -> None:
    raw = "Safe update failed: Download error"
    assert format_update_summary(raw).startswith("Update Status: Failed")
