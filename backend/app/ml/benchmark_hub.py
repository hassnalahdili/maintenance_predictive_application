from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import json
import os
import subprocess

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    IsolationForest,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import OneClassSVM

try:
    from xgboost import XGBClassifier, XGBRegressor
except Exception:  # noqa: BLE001
    XGBClassifier = None
    XGBRegressor = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "data" / "reports"
CATALOG_PATH = REPORT_DIR / "dataset_catalog.json"
OVERVIEW_PATH = REPORT_DIR / "ml_overview.json"

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


@dataclass
class DatasetCatalogEntry:
    dataset_id: str
    display_name: str
    machine_types: list[str]
    family: str
    tasks: list[str]
    format: str
    raw_path: str
    status: str
    note: str


def _ensure_output_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _coerce_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False).str.replace(" ", "", regex=False), errors="coerce")


def _coerce_numeric_value(value) -> float:
    text = str(value).strip().replace(",", ".").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def _parse_duration_minutes(value: str) -> float:
    clean = str(value).replace(" ", "")
    if ":" not in clean:
        return _coerce_numeric_value(clean)
    minutes, seconds = clean.split(":", maxsplit=1)
    return float(minutes or 0) + float(seconds or 0) / 60.0


def _summarize_matrix(matrix: pd.DataFrame, prefix: str) -> pd.DataFrame:
    numeric = matrix.apply(pd.to_numeric, errors="coerce")
    summary = pd.DataFrame(
        {
            f"{prefix}_mean": numeric.mean(axis=1),
            f"{prefix}_std": numeric.std(axis=1),
            f"{prefix}_min": numeric.min(axis=1),
            f"{prefix}_max": numeric.max(axis=1),
            f"{prefix}_rms": np.sqrt(np.square(numeric).mean(axis=1)),
        }
    )
    return summary


def _build_catalog() -> list[DatasetCatalogEntry]:
    entries: list[DatasetCatalogEntry] = []

    def add(
        dataset_id: str,
        display_name: str,
        machine_types: list[str],
        family: str,
        tasks: list[str],
        format_name: str,
        raw_path: Path,
        status: str,
        note: str,
    ) -> None:
        if raw_path.exists():
            entries.append(
                DatasetCatalogEntry(
                    dataset_id=dataset_id,
                    display_name=display_name,
                    machine_types=machine_types,
                    family=family,
                    tasks=tasks,
                    format=format_name,
                    raw_path=str(raw_path),
                    status=status,
                    note=note,
                )
            )

    add(
        "cwru_features",
        "CWRU Bearing Features",
        ["moteur", "generateur", "broyeur"],
        "machines_tournantes",
        ["classification", "anomaly_detection"],
        "csv",
        RAW_DIR / "archive (3)" / "feature_time_48k_2048_load_1.csv",
        "ready",
        "Jeu tabulaire benchmarkable pour défauts de roulements.",
    )
    add(
        "hydraulic_systems",
        "Hydraulic Systems",
        ["pompe"],
        "fluides",
        ["classification"],
        "txt-matrix",
        RAW_DIR / "condition+monitoring+of+hydraulic+systems",
        "ready",
        "Capteurs multi-sources avec etiquettes de degradation composant.",
    )
    add(
        "vibration_features",
        "Vibration Feature Dataset",
        ["compresseur", "ventilateur", "broyeur"],
        "machines_tournantes",
        ["classification", "anomaly_detection"],
        "csv",
        RAW_DIR / "vibration_dataset" / "vibration_dataset.csv",
        "ready",
        "Jeu tabulaire multiclasses exploitable immediatement.",
    )
    add(
        "metropt3",
        "MetroPT-3 Compressor",
        ["compresseur"],
        "fluides",
        ["sequence_classification", "replay"],
        "csv",
        RAW_DIR / "metropt+3+dataset" / "MetroPT3(AirCompressor).csv",
        "partial",
        "Series temporelles riches, preparees pour rejeu, etiquetage sequence encore a renforcer.",
    )
    add(
        "pump_timeseries",
        "Pump Time Series",
        ["pompe"],
        "fluides",
        ["replay"],
        "csv",
        RAW_DIR / "A_2024-04-10.csv",
        "partial",
        "Bon candidat de faux temps reel a partir de donnees reelles.",
    )
    add(
        "mimii_fan_audio",
        "MIMII Fan Audio",
        ["ventilateur"],
        "machines_tournantes",
        ["audio_anomaly_detection"],
        "wav",
        RAW_DIR / "-6_dB_fan",
        "partial",
        "Audio fan exploitable pour anomalies, feature engineering audio a ajouter.",
    )
    add(
        "dcase_fan_audio",
        "DCASE Fan Audio",
        ["ventilateur"],
        "machines_tournantes",
        ["audio_anomaly_detection"],
        "wav",
        RAW_DIR / "dev_data_fan",
        "partial",
        "Jeu audio de validation utile pour etude PFE fan.",
    )
    add(
        "ims_bearing_rul",
        "IMS Bearing RUL",
        ["moteur", "generateur", "broyeur"],
        "machines_tournantes",
        ["rul_regression"],
        "rar",
        RAW_DIR / "IMS",
        "ready",
        "Pipeline RUL prepare a partir des archives IMS avec echantillonnage temporel.",
    )
    add(
        "furnace_process",
        "Electric Arc Furnace",
        ["four"],
        "thermique",
        ["process_regression", "replay"],
        "csv",
        RAW_DIR / "archive (5)",
        "ready",
        "Agrégation par heat pour benchmark procédé thermique du four.",
    )
    return entries


def _prepare_cwru_dataset() -> dict | None:
    path = RAW_DIR / "archive (3)" / "feature_time_48k_2048_load_1.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)
    feature_columns = [column for column in df.columns if column != "fault"]

    def map_label(value: str) -> str:
        value = str(value)
        if value.startswith("Ball"):
            return "ball"
        if value.startswith("IR"):
            return "inner_race"
        if value.startswith("OR"):
            return "outer_race"
        return "normal"

    prepared = df[feature_columns].copy()
    prepared["fault_family"] = df["fault"].map(map_label)
    prepared["is_anomaly"] = (prepared["fault_family"] != "normal").astype(int)

    output_path = PROCESSED_DIR / "cwru_features.csv"
    prepared.to_csv(output_path, index=False)
    return {
        "dataset_id": "cwru_features",
        "display_name": "CWRU Bearing Features",
        "output_path": str(output_path),
        "rows": int(len(prepared)),
        "feature_count": len(feature_columns),
        "exclude_from_features": ["fault_family", "is_anomaly"],
        "task_targets": {
            "classification": "fault_family",
            "anomaly_detection": "is_anomaly",
        },
    }


def _prepare_vibration_dataset() -> dict | None:
    path = RAW_DIR / "vibration_dataset" / "vibration_dataset.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)
    feature_columns = [column for column in df.columns if column not in {"id", "label"}]
    prepared = df[feature_columns].copy()
    prepared["fault_label"] = df["label"].astype(int)
    prepared["is_anomaly"] = (prepared["fault_label"] != 0).astype(int)

    output_path = PROCESSED_DIR / "vibration_features.csv"
    prepared.to_csv(output_path, index=False)
    return {
        "dataset_id": "vibration_features",
        "display_name": "Vibration Feature Dataset",
        "output_path": str(output_path),
        "rows": int(len(prepared)),
        "feature_count": len(feature_columns),
        "exclude_from_features": ["fault_label", "is_anomaly"],
        "task_targets": {
            "classification": "fault_label",
            "anomaly_detection": "is_anomaly",
        },
    }


def _prepare_hydraulic_dataset() -> dict | None:
    base_dir = RAW_DIR / "condition+monitoring+of+hydraulic+systems"
    if not base_dir.exists():
        return None

    sensor_files = [
        "PS1.txt",
        "PS2.txt",
        "PS3.txt",
        "PS4.txt",
        "PS5.txt",
        "PS6.txt",
        "EPS1.txt",
        "FS1.txt",
        "FS2.txt",
        "TS1.txt",
        "TS2.txt",
        "TS3.txt",
        "TS4.txt",
        "VS1.txt",
        "CE.txt",
        "CP.txt",
    ]

    features = []
    for file_name in sensor_files:
        path = base_dir / file_name
        if not path.exists():
            continue
        matrix = pd.read_csv(path, sep="\t", header=None)
        features.append(_summarize_matrix(matrix, Path(file_name).stem.lower()))

    if not features:
        return None

    prepared = pd.concat(features, axis=1)
    profile = pd.read_csv(base_dir / "profile.txt", sep="\t", header=None)
    profile.columns = [
        "cooler_condition",
        "valve_condition",
        "pump_leakage",
        "accumulator_pressure",
        "stable_flag",
    ]
    prepared = pd.concat([prepared, profile], axis=1)
    prepared = prepared[prepared["stable_flag"] == 0].reset_index(drop=True)
    prepared["any_fault"] = (
        (prepared["cooler_condition"] != 100)
        | (prepared["valve_condition"] != 100)
        | (prepared["pump_leakage"] != 0)
        | (prepared["accumulator_pressure"] != 130)
    ).astype(int)

    output_path = PROCESSED_DIR / "hydraulic_features.csv"
    prepared.to_csv(output_path, index=False)
    return {
        "dataset_id": "hydraulic_systems",
        "display_name": "Hydraulic Systems",
        "output_path": str(output_path),
        "rows": int(len(prepared)),
        "feature_count": int(len(prepared.columns) - 6),
        "exclude_from_features": [
            "cooler_condition",
            "valve_condition",
            "pump_leakage",
            "accumulator_pressure",
            "stable_flag",
            "any_fault",
        ],
        "task_targets": {
            "classification": "any_fault",
        },
    }


def _prepare_furnace_dataset() -> dict | None:
    output_path = PROCESSED_DIR / "furnace_process_features.csv"
    if output_path.exists():
        cached = pd.read_csv(output_path)
        feature_columns = [column for column in cached.columns if column not in {"heat_id", "heat_datetime", "target_temp"}]
        return {
            "dataset_id": "furnace_process",
            "display_name": "Electric Arc Furnace",
            "output_path": str(output_path),
            "rows": int(len(cached)),
            "feature_count": len(feature_columns),
            "exclude_from_features": ["heat_id", "heat_datetime", "target_temp"],
            "task_targets": {
                "regression": "target_temp",
            },
            "sort_columns": ["heat_datetime"],
        }

    base_dir = RAW_DIR / "archive (5)"
    if not base_dir.exists():
        return None

    temp = pd.read_csv(base_dir / "eaf_temp.csv")
    temp["heat_datetime"] = pd.to_datetime(temp["DATETIME"], errors="coerce")
    temp["target_temp"] = _coerce_numeric_series(temp["TEMP"])
    temp["valo2_ppm"] = _coerce_numeric_series(temp["VALO2_PPM"])
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
    transformer["tap"] = _coerce_numeric_series(transformer["TAP"])
    transformer["mw"] = _coerce_numeric_series(transformer["MW"])
    transformer["duration_minutes"] = transformer["DURATION"].apply(_parse_duration_minutes)
    transformer = transformer.groupby("HEATID", as_index=False).agg(
        transformer_tap_mean=("tap", "mean"),
        transformer_tap_max=("tap", "max"),
        transformer_mw_mean=("mw", "mean"),
        transformer_mw_max=("mw", "max"),
        transformer_duration_total=("duration_minutes", "sum"),
    )

    gas = pd.read_csv(base_dir / "eaf_gaslance_mat.csv")
    gas["o2_amount"] = _coerce_numeric_series(gas["O2_AMOUNT"])
    gas["gas_amount"] = _coerce_numeric_series(gas["GAS_AMOUNT"])
    gas["o2_flow"] = _coerce_numeric_series(gas["O2_FLOW"])
    gas["gas_flow"] = _coerce_numeric_series(gas["GAS_FLOW"])
    gas = gas.groupby("HEATID", as_index=False).agg(
        gas_o2_amount_sum=("o2_amount", "sum"),
        gas_gas_amount_sum=("gas_amount", "sum"),
        gas_o2_flow_mean=("o2_flow", "mean"),
        gas_o2_flow_max=("o2_flow", "max"),
        gas_gas_flow_mean=("gas_flow", "mean"),
        gas_gas_flow_max=("gas_flow", "max"),
    )

    basket = pd.read_csv(base_dir / "basket_charged.csv", low_memory=False)
    basket["charged_amount"] = _coerce_numeric_series(basket["CHARGED_AMOUNT"])
    basket = basket.groupby("HEATID", as_index=False).agg(
        basket_events=("CHARGED_AMOUNT", "count"),
        basket_charged_sum=("charged_amount", "sum"),
    )

    materials = pd.read_csv(base_dir / "eaf_added_materials.csv")
    materials["charge_amount"] = _coerce_numeric_series(materials["CHARGE_AMOUNT"])
    materials = materials.groupby("HEATID", as_index=False).agg(
        material_events=("CHARGE_AMOUNT", "count"),
        material_charge_sum=("charge_amount", "sum"),
    )

    merged = temp.merge(transformer, on="HEATID", how="left")
    merged = merged.merge(gas, on="HEATID", how="left")
    merged = merged.merge(basket, on="HEATID", how="left")
    merged = merged.merge(materials, on="HEATID", how="left")
    merged = merged.rename(columns={"HEATID": "heat_id"})
    merged = merged.dropna(subset=["heat_datetime", "target_temp"]).sort_values("heat_datetime").reset_index(drop=True)
    merged["heat_datetime"] = merged["heat_datetime"].astype(str)

    merged.to_csv(output_path, index=False)
    feature_columns = [column for column in merged.columns if column not in {"heat_id", "heat_datetime", "target_temp"}]
    return {
        "dataset_id": "furnace_process",
        "display_name": "Electric Arc Furnace",
        "output_path": str(output_path),
        "rows": int(len(merged)),
        "feature_count": len(feature_columns),
        "exclude_from_features": ["heat_id", "heat_datetime", "target_temp"],
        "task_targets": {
            "regression": "target_temp",
        },
        "sort_columns": ["heat_datetime"],
    }


def _list_archive_members(archive_path: Path) -> list[str]:
    result = subprocess.run(["tar", "-tf", str(archive_path)], capture_output=True, text=True, check=True)
    members = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [member for member in members if Path(member).name.count(".") >= 5]


def _sample_members(members: list[str], max_samples: int = 80) -> list[str]:
    if len(members) <= max_samples:
        return members
    stride = max(1, len(members) // max_samples)
    selected = members[::stride]
    if members[-1] not in selected:
        selected.append(members[-1])
    return selected


def _extract_member_bytes(archive_path: Path, member: str) -> bytes:
    result = subprocess.run(["tar", "-xOf", str(archive_path), member], capture_output=True, check=True)
    return result.stdout


def _ims_member_timestamp(member: str) -> datetime:
    return datetime.strptime(Path(member).name, "%Y.%m.%d.%H.%M.%S")


def _prepare_ims_rul_dataset() -> dict | None:
    output_path = PROCESSED_DIR / "ims_rul_features.csv"
    if output_path.exists():
        cached = pd.read_csv(output_path)
        feature_columns = [column for column in cached.columns if column not in {"run_id", "timestamp", "rul_hours"}]
        return {
            "dataset_id": "ims_bearing_rul",
            "display_name": "IMS Bearing RUL",
            "output_path": str(output_path),
            "rows": int(len(cached)),
            "feature_count": len(feature_columns),
            "exclude_from_features": ["run_id", "timestamp", "rul_hours"],
            "task_targets": {
                "regression": "rul_hours",
            },
            "sort_columns": ["run_id", "timestamp"],
            "group_column": "run_id",
        }

    base_dir = RAW_DIR / "IMS" / "IMS"
    if not base_dir.exists():
        return None

    archives = [path for path in (base_dir / "1st_test.rar", base_dir / "2nd_test.rar", base_dir / "3rd_test.rar") if path.exists()]
    rows: list[dict] = []
    for archive_path in archives:
        members = _sample_members(_list_archive_members(archive_path), max_samples=80)
        timed_members = sorted(((member, _ims_member_timestamp(member)) for member in members), key=lambda item: item[1])
        if not timed_members:
            continue
        start_time = timed_members[0][1]
        end_time = timed_members[-1][1]

        for member, current_time in timed_members:
            matrix = np.loadtxt(BytesIO(_extract_member_bytes(archive_path, member)))
            if matrix.ndim == 1:
                matrix = matrix.reshape(-1, 1)
            matrix = np.asarray(matrix, dtype=float)

            row = {
                "run_id": archive_path.stem,
                "timestamp": current_time.isoformat(),
                "elapsed_hours": round((current_time - start_time).total_seconds() / 3600, 4),
                "rul_hours": round((end_time - current_time).total_seconds() / 3600, 4),
            }
            channels = min(matrix.shape[1], 8)
            for channel_idx in range(channels):
                channel = matrix[:, channel_idx]
                row[f"ch{channel_idx + 1}_mean"] = float(np.mean(channel))
                row[f"ch{channel_idx + 1}_std"] = float(np.std(channel))
                row[f"ch{channel_idx + 1}_rms"] = float(np.sqrt(np.mean(np.square(channel))))
            row["signal_mean_abs"] = float(np.mean(np.abs(matrix)))
            row["signal_max_abs"] = float(np.max(np.abs(matrix)))
            row["signal_std"] = float(np.std(matrix))
            rows.append(row)

    if not rows:
        return None

    prepared = pd.DataFrame(rows).sort_values(["run_id", "timestamp"]).reset_index(drop=True)
    prepared.to_csv(output_path, index=False)
    feature_columns = [column for column in prepared.columns if column not in {"run_id", "timestamp", "rul_hours"}]
    return {
        "dataset_id": "ims_bearing_rul",
        "display_name": "IMS Bearing RUL",
        "output_path": str(output_path),
        "rows": int(len(prepared)),
        "feature_count": len(feature_columns),
        "exclude_from_features": ["run_id", "timestamp", "rul_hours"],
        "task_targets": {
            "regression": "rul_hours",
        },
        "sort_columns": ["run_id", "timestamp"],
        "group_column": "run_id",
    }


def _classification_models(class_count: int) -> dict[str, object]:
    models: dict[str, object] = {
        "LogisticRegression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
            ]
        ),
        "RandomForest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=250,
                        max_depth=None,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
        "HistGradientBoosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", HistGradientBoostingClassifier(random_state=42)),
            ]
        ),
    }
    if XGBClassifier is not None:
        xgb_kwargs = {
            "n_estimators": 250,
            "learning_rate": 0.05,
            "max_depth": 6,
            "subsample": 0.9,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": 1,
        }
        if class_count > 2:
            xgb_kwargs.update({"objective": "multi:softprob", "num_class": class_count, "eval_metric": "mlogloss"})
        else:
            xgb_kwargs.update({"objective": "binary:logistic", "eval_metric": "logloss"})
        models["XGBoost"] = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", XGBClassifier(**xgb_kwargs)),
            ]
        )
    return models


def _regression_models() -> dict[str, object]:
    models: dict[str, object] = {
        "LinearRegression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ]
        ),
        "RandomForestRegressor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=250,
                        min_samples_leaf=2,
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
        "HistGradientBoostingRegressor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", HistGradientBoostingRegressor(random_state=42)),
            ]
        ),
    }
    if XGBRegressor is not None:
        models["XGBoostRegressor"] = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    XGBRegressor(
                        n_estimators=250,
                        learning_rate=0.05,
                        max_depth=6,
                        subsample=0.9,
                        colsample_bytree=0.8,
                        objective="reg:squarederror",
                        eval_metric="rmse",
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        )
    return models


def _benchmark_classification(df: pd.DataFrame, target_column: str, exclude_columns: list[str] | None = None) -> dict:
    excluded = set(exclude_columns or [])
    feature_columns = [column for column in df.columns if column != target_column and column not in excluded]
    X = df[feature_columns]
    y_raw = df[target_column]

    encoder = LabelEncoder()
    y = encoder.fit_transform(y_raw)
    class_count = int(len(encoder.classes_))

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    results = []
    for model_name, model in _classification_models(class_count).items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        result = {
            "model": model_name,
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "f1_macro": round(float(f1_score(y_test, predictions, average="macro")), 4),
            "recall_macro": round(float(recall_score(y_test, predictions, average="macro")), 4),
            "precision_macro": round(float(precision_score(y_test, predictions, average="macro", zero_division=0)), 4),
        }
        results.append(result)

    ordered = sorted(results, key=lambda item: item["f1_macro"], reverse=True)
    return {
        "primary_metric": "f1_macro",
        "rows": int(len(df)),
        "features": len(feature_columns),
        "classes": int(class_count),
        "results": ordered,
        "winner": ordered[0]["model"] if ordered else None,
    }


def _score_to_auc(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    try:
        return round(float(roc_auc_score(y_true, scores)), 4)
    except Exception:  # noqa: BLE001
        return None


def _benchmark_anomaly(df: pd.DataFrame, target_column: str, exclude_columns: list[str] | None = None) -> dict:
    excluded = set(exclude_columns or [])
    feature_columns = [column for column in df.columns if column != target_column and column not in excluded]
    X = df[feature_columns].apply(pd.to_numeric, errors="coerce")
    y = df[target_column].astype(int).to_numpy()

    normal_mask = y == 0
    X_normal = X.loc[normal_mask]
    X_anomaly = X.loc[~normal_mask]

    X_train, X_test_normal = train_test_split(X_normal, test_size=0.3, random_state=42)
    X_test = pd.concat([X_test_normal, X_anomaly], axis=0).reset_index(drop=True)
    y_test = np.concatenate([np.zeros(len(X_test_normal), dtype=int), np.ones(len(X_anomaly), dtype=int)])

    models = {
        "IsolationForest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", IsolationForest(random_state=42, contamination=0.1, n_estimators=250)),
            ]
        ),
        "OneClassSVM": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", OneClassSVM(gamma="scale", nu=0.1)),
            ]
        ),
        "LocalOutlierFactor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LocalOutlierFactor(novelty=True, contamination=0.1)),
            ]
        ),
    }

    results = []
    for model_name, model in models.items():
        model.fit(X_train)
        predictions = (model.predict(X_test) == -1).astype(int)

        anomaly_scores = None
        model_step = model.named_steps["model"]
        transformed = model[:-1].transform(X_test) if len(model.steps) > 1 else X_test
        if hasattr(model_step, "score_samples"):
            anomaly_scores = -model_step.score_samples(transformed)
        elif hasattr(model_step, "decision_function"):
            anomaly_scores = -model_step.decision_function(transformed)

        results.append(
            {
                "model": model_name,
                "precision_anomaly": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
                "recall_anomaly": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
                "f1_anomaly": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
                "roc_auc": _score_to_auc(y_test, anomaly_scores) if anomaly_scores is not None else None,
            }
        )

    ordered = sorted(results, key=lambda item: item["f1_anomaly"], reverse=True)
    return {
        "primary_metric": "f1_anomaly",
        "rows": int(len(df)),
        "features": len(feature_columns),
        "results": ordered,
        "winner": ordered[0]["model"] if ordered else None,
    }


def _temporal_regression_split(
    df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    *,
    sort_columns: list[str],
    group_column: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    ordered = df.sort_values(sort_columns).reset_index(drop=True)
    if group_column:
        train_parts = []
        test_parts = []
        for _, group in ordered.groupby(group_column, sort=False):
            if len(group) < 4:
                train_parts.append(group.iloc[:-1] if len(group) > 1 else group)
                test_parts.append(group.iloc[-1:] if len(group) > 1 else group.iloc[0:0])
                continue
            split_index = max(1, int(len(group) * 0.75))
            split_index = min(split_index, len(group) - 1)
            train_parts.append(group.iloc[:split_index])
            test_parts.append(group.iloc[split_index:])
        train_df = pd.concat(train_parts, axis=0).reset_index(drop=True)
        test_df = pd.concat(test_parts, axis=0).reset_index(drop=True)
    else:
        split_index = max(1, int(len(ordered) * 0.75))
        split_index = min(split_index, len(ordered) - 1)
        train_df = ordered.iloc[:split_index].reset_index(drop=True)
        test_df = ordered.iloc[split_index:].reset_index(drop=True)

    X_train = train_df[feature_columns]
    X_test = test_df[feature_columns]
    y_train = pd.to_numeric(train_df[target_column], errors="coerce")
    y_test = pd.to_numeric(test_df[target_column], errors="coerce")
    return X_train, X_test, y_train, y_test


def _benchmark_regression(
    df: pd.DataFrame,
    target_column: str,
    *,
    exclude_columns: list[str] | None = None,
    sort_columns: list[str] | None = None,
    group_column: str | None = None,
) -> dict:
    excluded = set(exclude_columns or [])
    feature_columns = [column for column in df.columns if column != target_column and column not in excluded]

    clean = df.copy()
    clean[target_column] = pd.to_numeric(clean[target_column], errors="coerce")
    clean = clean.dropna(subset=[target_column]).reset_index(drop=True)

    if sort_columns:
        X_train, X_test, y_train, y_test = _temporal_regression_split(
            clean,
            feature_columns,
            target_column,
            sort_columns=sort_columns,
            group_column=group_column,
        )
    else:
        X = clean[feature_columns]
        y = clean[target_column]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    results = []
    for model_name, model in _regression_models().items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
        results.append(
            {
                "model": model_name,
                "mae": round(float(mean_absolute_error(y_test, predictions)), 4),
                "rmse": round(rmse, 4),
                "r2": round(float(r2_score(y_test, predictions)), 4),
            }
        )

    ordered = sorted(results, key=lambda item: item["rmse"])
    return {
        "primary_metric": "rmse",
        "rows": int(len(clean)),
        "features": len(feature_columns),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "results": ordered,
        "winner": ordered[0]["model"] if ordered else None,
    }


def _prepared_datasets() -> list[dict]:
    prepared = []
    for builder in (
        _prepare_cwru_dataset,
        _prepare_vibration_dataset,
        _prepare_hydraulic_dataset,
        _prepare_furnace_dataset,
        _prepare_ims_rul_dataset,
    ):
        dataset = builder()
        if dataset:
            prepared.append(dataset)
    return prepared


def build_ml_overview() -> dict:
    _ensure_output_dirs()
    catalog_entries = _build_catalog()
    prepared = _prepared_datasets()

    benchmarks = []
    for dataset in prepared:
        dataset_path = Path(dataset["output_path"])
        df = pd.read_csv(dataset_path)
        task_targets = dataset["task_targets"]
        exclude_from_features = dataset.get("exclude_from_features", [])
        sort_columns = dataset.get("sort_columns")
        group_column = dataset.get("group_column")

        if "classification" in task_targets:
            benchmarks.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "display_name": dataset["display_name"],
                    "task": "classification",
                    **_benchmark_classification(df, task_targets["classification"], exclude_from_features),
                }
            )
        if "anomaly_detection" in task_targets:
            benchmarks.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "display_name": dataset["display_name"],
                    "task": "anomaly_detection",
                    **_benchmark_anomaly(df, task_targets["anomaly_detection"], exclude_from_features),
                }
            )
        if "regression" in task_targets:
            benchmarks.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "display_name": dataset["display_name"],
                    "task": "regression",
                    **_benchmark_regression(
                        df,
                        task_targets["regression"],
                        exclude_columns=exclude_from_features,
                        sort_columns=sort_columns,
                        group_column=group_column,
                    ),
                }
            )

    winners = [
        {
            "dataset_id": benchmark["dataset_id"],
            "display_name": benchmark["display_name"],
            "task": benchmark["task"],
            "winner": benchmark["winner"],
            "primary_metric": benchmark["primary_metric"],
            "primary_value": benchmark["results"][0][benchmark["primary_metric"]] if benchmark["results"] else None,
        }
        for benchmark in benchmarks
    ]

    overview = {
        "generated_at": _utc_now(),
        "paths": {
            "raw": str(RAW_DIR),
            "processed": str(PROCESSED_DIR),
            "reports": str(REPORT_DIR),
        },
        "summary": {
            "detected_datasets": len(catalog_entries),
            "ready_datasets": sum(1 for entry in catalog_entries if entry.status == "ready"),
            "partial_datasets": sum(1 for entry in catalog_entries if entry.status == "partial"),
            "prepared_datasets": len(prepared),
            "benchmark_runs": len(benchmarks),
        },
        "catalog": [asdict(entry) for entry in catalog_entries],
        "prepared_datasets": prepared,
        "benchmarks": benchmarks,
        "winners": winners,
        "recommendations": [
            "Renforcer MetroPT-3 avec etiquettes sequence de panne pour un benchmark compresseur plus industriel.",
            "Ajouter une cible qualite/energie sur le four en plus de la regression de temperature.",
            "Exploiter les jeux audio fan pour une piste anomaly detection multimodale.",
            "Relier les benchmarks gagnants au deploiement modele par famille de machines.",
        ],
    }

    CATALOG_PATH.write_text(json.dumps(overview["catalog"], indent=2, ensure_ascii=False), encoding="utf-8")
    OVERVIEW_PATH.write_text(json.dumps(overview, indent=2, ensure_ascii=False), encoding="utf-8")
    return overview


def get_ml_overview(*, refresh: bool = False) -> dict:
    if not refresh and OVERVIEW_PATH.exists():
        return json.loads(OVERVIEW_PATH.read_text(encoding="utf-8"))
    return build_ml_overview()
