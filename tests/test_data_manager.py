import pandas as pd

from core.data.data_manager import MissionDataService


def test_normalizes_mega_city_to_mega_structure(tmp_path):
    service = MissionDataService()
    excel_path = tmp_path / "mission.xlsx"

    input_df = pd.DataFrame(
        [
            {"Planet": "A", "Mega City": "MC", "Kills": 10},
        ]
    )
    input_df.to_excel(excel_path, index=False)

    df = service.read_mission_log(str(excel_path), use_cache=False)
    assert "Mega Structure" in df.columns
    assert "Mega City" not in df.columns
    assert df.iloc[0]["Mega Structure"] == "MC"


def test_append_mission_updates_last_row_cache(tmp_path):
    service = MissionDataService()
    excel_path = tmp_path / "mission.xlsx"

    assert service.append_mission(str(excel_path), {"Planet": "Super Earth", "Kills": 1})
    assert service.append_mission(str(excel_path), {"Planet": "Mars", "Kills": 3})

    last_row = service.get_last_mission_row(str(excel_path), use_cache=True)
    assert last_row is not None
    assert last_row["Planet"] == "Mars"

    df = service.read_mission_log(str(excel_path), use_cache=False)
    assert len(df) == 2
