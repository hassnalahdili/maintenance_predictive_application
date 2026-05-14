from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import Machine
from app.services.maintenance_service import process_sensor_reading, serialize_prediction


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

_REPLAY_CACHE: dict[str, dict] = {}
_REPLAY_STATE: dict[str, int] = {}


def _rescale_series(series: pd.Series, low: float, high: float) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    minimum = numeric.min()
    maximum = numeric.max()
    if pd.isna(minimum) or pd.isna(maximum) or maximum <= minimum:
        return pd.Series([round((low + high) / 2, 4)] * len(numeric), index=numeric.index)
    scaled = low + ((numeric - minimum) / (maximum - minimum)) * (high - low)
    return scaled.clip(low, high).round(4)


def _build_pump_replay(source_id: str, file_name: str, prefix: str) -> dict:
    path = RAW_DIR / file_name
    df = pd.read_csv(path)
    frame = pd.DataFrame()
    frame["timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce", utc=True).dt.tz_convert(None)
    frame["temperature"] = _rescale_series(df[f"{prefix}_Temp.PV"], 60, 96)
    frame["pressure"] = _rescale_series(df[f"{prefix}_Pres.PV"], 5.8, 8.4)
    frame["rpm"] = _rescale_series(df[f"{prefix}_ACR_Mot.SV"], 1360, 1540)
    frame["current"] = _rescale_series(df[f"{prefix}_ACR_Mot.TV"], 42, 68)
    vibration_signal = (
        pd.to_numeric(df[f"{prefix}_ACR_Mot.TV"], errors="coerce").sub(pd.to_numeric(df[f"{prefix}_ACR_Pmp.TV"], errors="coerce")).abs()
        + pd.to_numeric(df[f"{prefix}_Temp.PV"], errors="coerce").sub(pd.to_numeric(df["Temperature"], errors="coerce")).abs()
        + pd.to_numeric(df[f"{prefix}_ACR_Mot.SV"], errors="coerce").sub(pd.to_numeric(df[f"{prefix}_ACR_Pmp.SV"], errors="coerce")).abs()
    )
    vibration = _rescale_series(vibration_signal, 1.2, 5.4)
    frame["vibration_x"] = vibration
    frame["vibration_y"] = (vibration * 0.97).round(4)
    frame["vibration_z"] = (vibration * 1.03).round(4)
    frame = frame.dropna().reset_index(drop=True)
    return {
        "source_id": source_id,
        "display_name": f"Replay pompe {prefix}",
        "machine_type": "pompe",
        "description": f"Rejeu temps reel base sur le fichier {file_name}",
        "frame": frame,
    }


def _build_compressor_replay() -> dict:
    path = RAW_DIR / "metropt+3+dataset" / "MetroPT3(AirCompressor).csv"
    df = pd.read_csv(path)
    df = df.iloc[::300].reset_index(drop=True)
    frame = pd.DataFrame()
    frame["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.tz_localize(None)
    frame["temperature"] = _rescale_series(df["Oil_temperature"], 68, 97)
    pressure_signal = pd.to_numeric(df["TP3"], errors="coerce").fillna(0) + pd.to_numeric(df["Reservoirs"], errors="coerce").fillna(0)
    frame["pressure"] = _rescale_series(pressure_signal, 6.0, 8.7)
    frame["rpm"] = _rescale_series(pd.to_numeric(df["COMP"], errors="coerce").fillna(0) + pd.to_numeric(df["Pressure_switch"], errors="coerce").fillna(0), 1380, 1560)
    frame["current"] = _rescale_series(df["Motor_current"], 40, 74)
    vibration_signal = (
        pd.to_numeric(df["DV_pressure"], errors="coerce").abs().fillna(0)
        + pd.to_numeric(df["Caudal_impulses"], errors="coerce").fillna(0)
        + pd.to_numeric(df["LPS"], errors="coerce").fillna(0)
    )
    vibration = _rescale_series(vibration_signal, 1.4, 5.8)
    frame["vibration_x"] = vibration
    frame["vibration_y"] = (vibration * 0.98).round(4)
    frame["vibration_z"] = (vibration * 1.02).round(4)
    frame = frame.dropna().reset_index(drop=True)
    return {
        "source_id": "metropt3_replay",
        "display_name": "Replay compresseur MetroPT-3",
        "machine_type": "compresseur",
        "description": "Rejeu temps reel base sur le dataset MetroPT-3",
        "frame": frame,
    }


def _load_furnace_features() -> pd.DataFrame:
    processed = PROCESSED_DIR / "furnace_process_features.csv"
    if processed.exists():
        return pd.read_csv(processed)

    base_dir = RAW_DIR / "archive (5)"
    temp = pd.read_csv(base_dir / "eaf_temp.csv")
    temp["heat_datetime"] = pd.to_datetime(temp["DATETIME"], errors="coerce")
    temp["target_temp"] = pd.to_numeric(temp["TEMP"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    temp["valo2_ppm"] = pd.to_numeric(temp["VALO2_PPM"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    temp = (
        temp.sort_values("heat_datetime")
        .groupby("HEATID", as_index=False)
        .agg(
            heat_datetime=("heat_datetime", "max"),
            target_temp=("target_temp", "max"),
            valo2_ppm_mean=("valo2_ppm", "mean"),
            valo2_ppm_max=("valo2_ppm", "max"),
        )
    )

    transformer = pd.read_csv(base_dir / "eaf_transformer.csv")
    transformer["tap"] = pd.to_numeric(transformer["TAP"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    transformer["mw"] = pd.to_numeric(transformer["MW"].astype(str).str.replace(",", ".", regex=False).str.replace(" ", "", regex=False), errors="coerce")
    transformer["duration_minutes"] = transformer["DURATION"].astype(str).str.replace(" ", "", regex=False).map(
        lambda value: float(value.split(":")[0]) + float(value.split(":")[1]) / 60 if ":" in value else 0.0
    )
    transformer = transformer.groupby("HEATID", as_index=False).agg(
        transformer_tap_mean=("tap", "mean"),
        transformer_tap_max=("tap", "max"),
        transformer_mw_mean=("mw", "mean"),
        transformer_mw_max=("mw", "max"),
        transformer_duration_total=("duration_minutes", "sum"),
    )

    gas = pd.read_csv(base_dir / "eaf_gaslance_mat.csv")
    for source, target in [("O2_AMOUNT", "o2_amount"), ("GAS_AMOUNT", "gas_amount"), ("O2_FLOW", "o2_flow"), ("GAS_FLOW", "gas_flow")]:
        gas[target] = pd.to_numeric(gas[source].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    gas = gas.groupby("HEATID", as_index=False).agg(
        gas_o2_amount_sum=("o2_amount", "sum"),
        gas_gas_amount_sum=("gas_amount", "sum"),
        gas_o2_flow_mean=("o2_flow", "mean"),
        gas_o2_flow_max=("o2_flow", "max"),
        gas_gas_flow_mean=("gas_flow", "mean"),
        gas_gas_flow_max=("gas_flow", "max"),
    )

    merged = temp.merge(transformer, on="HEATID", how="left").merge(gas, on="HEATID", how="left")
    merged = merged.rename(columns={"HEATID": "heat_id"}).dropna(subset=["heat_datetime", "target_temp"]).sort_values("heat_datetime")
    return merged.reset_index(drop=True)


def _build_furnace_replay() -> dict:
    df = _load_furnace_features()
    frame = pd.DataFrame()
    frame["timestamp"] = pd.to_datetime(df["heat_datetime"], errors="coerce")
    frame["temperature"] = _rescale_series(df["target_temp"], 780, 990)
    frame["pressure"] = _rescale_series(df["valo2_ppm_max"], 0.9, 1.6)
    frame["rpm"] = _rescale_series(df["transformer_tap_max"], 240, 420)
    frame["current"] = _rescale_series(df["transformer_mw_mean"], 56, 84)
    vibration_signal = pd.to_numeric(df["gas_o2_flow_max"], errors="coerce").fillna(0) + pd.to_numeric(df["transformer_duration_total"], errors="coerce").fillna(0)
    vibration = _rescale_series(vibration_signal, 0.8, 2.8)
    frame["vibration_x"] = vibration
    frame["vibration_y"] = (vibration * 0.95).round(4)
    frame["vibration_z"] = (vibration * 1.05).round(4)
    frame = frame.dropna().reset_index(drop=True)
    return {
        "source_id": "furnace_replay",
        "display_name": "Replay four industriel",
        "machine_type": "four",
        "description": "Rejeu temps reel base sur les heats du four electrique",
        "frame": frame,
    }


def _source_definitions() -> dict[str, callable]:
    return {
        "pump_a_replay": lambda: _build_pump_replay("pump_a_replay", "A_2024-04-10.csv", "A"),
        "pump_b_replay": lambda: _build_pump_replay("pump_b_replay", "B_2024-04-10.csv", "B"),
        "pump_c_replay": lambda: _build_pump_replay("pump_c_replay", "C_2024-04-10.csv", "C"),
        "metropt3_replay": _build_compressor_replay,
        "furnace_replay": _build_furnace_replay,
    }


def _get_source(source_id: str) -> dict:
    if source_id not in _REPLAY_CACHE:
        builder = _source_definitions().get(source_id)
        if builder is None:
            raise KeyError(source_id)
        _REPLAY_CACHE[source_id] = builder()
        _REPLAY_STATE.setdefault(source_id, 0)
    return _REPLAY_CACHE[source_id]


def list_replay_sources() -> list[dict]:
    sources = []
    for source_id in _source_definitions():
        source = _get_source(source_id)
        cursor = _REPLAY_STATE.get(source_id, 0)
        row_count = len(source["frame"])
        sources.append(
            {
                "source_id": source_id,
                "display_name": source["display_name"],
                "machine_type": source["machine_type"],
                "description": source["description"],
                "row_count": row_count,
                "cursor": cursor,
                "completed": cursor >= row_count,
            }
        )
    return sources


def reset_replay_state(source_id: str | None = None) -> None:
    if source_id is None:
        for key in list(_REPLAY_STATE):
            _REPLAY_STATE[key] = 0
        return
    _REPLAY_STATE[source_id] = 0


def replay_step(db: Session, machine: Machine, *, source_id: str, steps: int = 1, reset: bool = False) -> dict:
    source = _get_source(source_id)
    if source["machine_type"] != machine.machine_type:
        raise ValueError("Le type de machine ne correspond pas a la source de rejeu selectionnee.")

    if reset:
        _REPLAY_STATE[source_id] = 0

    frame = source["frame"]
    cursor = _REPLAY_STATE.get(source_id, 0)
    injected_rows = 0
    latest_prediction = None
    latest_timestamp = None

    for _ in range(steps):
        if cursor >= len(frame):
            break
        row = frame.iloc[cursor]
        payload = {
            "machine_id": machine.id,
            "timestamp": pd.Timestamp(row["timestamp"]).to_pydatetime(),
            "temperature": float(row["temperature"]),
            "vibration_x": float(row["vibration_x"]),
            "vibration_y": float(row["vibration_y"]),
            "vibration_z": float(row["vibration_z"]),
            "pressure": float(row["pressure"]),
            "rpm": float(row["rpm"]),
            "current": float(row["current"]),
        }
        result = process_sensor_reading(db, machine, payload)
        latest_prediction = serialize_prediction(result["prediction"]).model_dump()
        latest_timestamp = payload["timestamp"]
        cursor += 1
        injected_rows += 1

    _REPLAY_STATE[source_id] = cursor
    return {
        "source_id": source_id,
        "machine_id": machine.id,
        "machine_name": machine.name,
        "machine_type": machine.machine_type,
        "injected_rows": injected_rows,
        "cursor": cursor,
        "completed": cursor >= len(frame),
        "latest_timestamp": latest_timestamp,
        "latest_prediction": latest_prediction,
    }
