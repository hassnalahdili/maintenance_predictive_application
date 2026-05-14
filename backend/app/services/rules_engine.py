from typing import Iterable
from app.models.models import BusinessRule, SensorData


def compare(value: float, operator: str, threshold: float) -> bool:
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == "==":
        return value == threshold
    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_rules(sensor: SensorData, rules: Iterable[BusinessRule]) -> list[BusinessRule]:
    matched = []
    for rule in rules:
        metric_value = getattr(sensor, rule.metric, None)
        if metric_value is None:
            continue
        if compare(float(metric_value), rule.operator, rule.threshold):
            matched.append(rule)
    return matched


def build_rule_features(sensor: SensorData, matched_rules: list[BusinessRule]) -> dict:
    total_vibration = float(sensor.vibration_x + sensor.vibration_y + sensor.vibration_z)
    max_confidence = max((r.confidence for r in matched_rules), default=0.0)
    severity_score = sum(
        4 if r.severity == "critical" else 3 if r.severity == "high" else 2 if r.severity == "medium" else 1
        for r in matched_rules
    )
    return {
        "temperature": sensor.temperature,
        "pressure": sensor.pressure,
        "rpm": sensor.rpm,
        "current": sensor.current,
        "total_vibration": total_vibration,
        "rule_count": len(matched_rules),
        "max_rule_confidence": max_confidence,
        "severity_score": severity_score,
        "temperature_margin_85": sensor.temperature - 85,
        "pressure_margin_7": sensor.pressure - 7,
        "rpm_drop_margin": 1450 - sensor.rpm,
    }


def compute_rule_based_probability(features: dict) -> float:
    score = 0.0
    score += min(max(features["rule_count"] * 0.15, 0), 0.45)
    score += 0.15 if features["temperature"] > 85 else 0
    score += 0.1 if features["total_vibration"] > 12 else 0
    score += 0.1 if features["pressure"] > 7.5 else 0
    score += 0.1 if features["rpm"] < 1400 else 0
    score += 0.1 if features["current"] > 55 else 0
    return round(min(score, 0.99), 4)


def risk_level(probability: float) -> str:
    if probability > 0.8:
        return "critical"
    if probability > 0.6:
        return "high"
    if probability > 0.4:
        return "medium"
    if probability > 0.2:
        return "low"
    return "normal"
