import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

import freightcli


runner = CliRunner()


def _configure_test_paths(monkeypatch, tmp_path):
    data_dir = tmp_path / "freightcli-data"
    downloads_dir = data_dir / "downloads"
    db_path = data_dir / "data.db"
    output_dir = tmp_path / "site-data"

    monkeypatch.setattr(freightcli, "DATA_DIR", data_dir)
    monkeypatch.setattr(freightcli, "DOWNLOADS_DIR", downloads_dir)
    monkeypatch.setattr(freightcli, "DB_PATH", db_path)
    monkeypatch.setattr(freightcli, "DEFAULT_OUTPUT_DIR", output_dir)

    freightcli.init_db()
    return downloads_dir, db_path, output_dir


def _insert_download_record(
    db_path: Path,
    source_name: str,
    zone: str,
    file_path: Path,
    realtime: bool = False,
    downloaded_at: str | None = None,
):
    file_hash = freightcli.get_file_hash(file_path)
    file_size = file_path.stat().st_size

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sources WHERE name = ?", (source_name,))
    source_id = cursor.fetchone()[0]
    if downloaded_at is None:
        cursor.execute(
            """
            INSERT INTO downloads (source_id, zone, file_path, file_hash, file_size, realtime)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source_id, zone, str(file_path), file_hash, file_size, realtime),
        )
    else:
        cursor.execute(
            """
            INSERT INTO downloads (source_id, zone, file_path, file_hash, file_size, realtime, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, zone, str(file_path), file_hash, file_size, realtime, downloaded_at),
        )
    conn.commit()
    conn.close()


def test_infer_cargo_from_ship_type_maps_expected_ranges():
    assert freightcli.infer_cargo_from_ship_type(70) == "general_cargo"
    assert freightcli.infer_cargo_from_ship_type(82) == "crude_oil"
    assert freightcli.infer_cargo_from_ship_type(88) == "petroleum"
    assert freightcli.infer_cargo_from_ship_type(999) == "containers"


def test_is_in_zone_handles_known_and_unknown_zones():
    assert freightcli.is_in_zone(25.0, -90.0, "Gulf_of_Mexico") is True
    assert freightcli.is_in_zone(50.0, -90.0, "Gulf_of_Mexico") is False
    assert freightcli.is_in_zone(0.0, 0.0, "Unknown_Zone") is True


def test_fetch_ships_data_falls_back_to_mock_without_credentials(monkeypatch):
    monkeypatch.delenv("AISHUB_USERNAME", raising=False)

    data = freightcli.fetch_ships_data("West_Coast_US", realtime=False)

    assert "ships" in data
    assert len(data["ships"]) >= 1
    assert data["ships"][0]["cargo"] == "containers"


def test_pipeline_format_outputs_zone_json(monkeypatch, tmp_path):
    downloads_dir, db_path, output_dir = _configure_test_paths(monkeypatch, tmp_path)

    ship_file = downloads_dir / "ships_marinetraffic" / "Gulf_of_Mexico_seed.json"
    ship_file.parent.mkdir(parents=True, exist_ok=True)
    ship_file.write_text(
        json.dumps(
            {
                "ships": [
                    {"mmsi": "1", "lat": 28.5, "lon": -90.0, "cargo": "containers", "eta": "2026-02-06T14:00:00Z"},
                    {"mmsi": "2", "lat": 55.0, "lon": -90.0, "cargo": "coal"},
                ]
            }
        )
    )
    _insert_download_record(
        db_path,
        "ships_marinetraffic",
        "Gulf_of_Mexico",
        ship_file,
        realtime=True,
        downloaded_at="2026-03-01 12:34:56",
    )

    train_file = downloads_dir / "trains_aar" / "Gulf_of_Mexico_seed.json"
    train_file.parent.mkdir(parents=True, exist_ok=True)
    train_file.write_text(
        json.dumps(
            {"trains": [{"train_id": "CN1234", "lat": 29.5, "lon": -90.5, "cargo": "grain", "destination": "New Orleans"}]}
        )
    )
    _insert_download_record(
        db_path,
        "trains_aar",
        "Gulf_of_Mexico",
        train_file,
        downloaded_at="2026-03-02 08:00:00",
    )

    truck_file = downloads_dir / "trucks_fmcsa" / "Gulf_of_Mexico_seed.json"
    truck_file.parent.mkdir(parents=True, exist_ok=True)
    truck_file.write_text(
        json.dumps(
            {"trucks": [{"truck_id": "TRK001", "lat": 29.8, "lon": -95.0, "cargo": "steel", "destination": "Houston"}]}
        )
    )
    _insert_download_record(
        db_path,
        "trucks_fmcsa",
        "Gulf_of_Mexico",
        truck_file,
        downloaded_at="2026-03-03 09:15:00",
    )

    result = runner.invoke(
        freightcli.app,
        ["pipeline", "format", "--zone", "Gulf_of_Mexico", "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0
    output_file = output_dir / "Gulf_of_Mexico.json"
    assert output_file.exists()

    formatted = json.loads(output_file.read_text())
    assert formatted["zone"] == "Gulf_of_Mexico"
    assert formatted["updated_at"] == "2026-03-03 09:15:00"
    assert len(formatted["transports"]) == 3
    assert {item["type"] for item in formatted["transports"]} == {"ship", "train", "truck"}
    assert {item["cargo_hs"] for item in formatted["transports"]} >= {"8609", "1001", "7208"}
