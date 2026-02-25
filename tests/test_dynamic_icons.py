import pandas as pd

from core.dynamic_icons import _compute_dynamic_data_from_df


def test_compute_dynamic_data_from_df():
    df = pd.DataFrame(
        [
            {"Time": "01-01-2025 10:00:00", "Planet": "Earth", "Kills": 5, "Deaths": 1},
            {"Time": "02-01-2025 10:00:00", "Planet": "Mars", "Kills": 9, "Deaths": 3},
            {"Time": "03-01-2025 10:00:00", "Planet": "Mars", "Kills": 1, "Deaths": 1},
        ]
    )

    data = _compute_dynamic_data_from_df(df)

    assert data["first_ingress"] == "Earth"
    assert data["favourite_planet"] == "Mars"
    assert data["highest_kills_planet"] == "Mars"
    assert data["highest_deaths_planet"] == "Mars"
