from __future__ import annotations
import random
from app.models.models import Machine, SensorData

BASELINES = {
    "moteur": {"temperature": 72, "pressure": 6.5, "rpm": 1500, "current": 48, "vibration": 2.4},
    "pompe": {"temperature": 68, "pressure": 7.2, "rpm": 1450, "current": 46, "vibration": 2.0},
    "convoyeur": {"temperature": 64, "pressure": 6.1, "rpm": 1380, "current": 44, "vibration": 1.8},
    "compresseur": {"temperature": 77, "pressure": 8.0, "rpm": 1520, "current": 55, "vibration": 2.6},
    "ventilateur": {"temperature": 66, "pressure": 6.0, "rpm": 1470, "current": 42, "vibration": 2.2},
    "generateur": {"temperature": 74, "pressure": 6.8, "rpm": 1500, "current": 58, "vibration": 2.7},
    "broyeur": {"temperature": 79, "pressure": 7.5, "rpm": 1410, "current": 62, "vibration": 3.2},
    "four": {"temperature": 840, "pressure": 1.1, "rpm": 320, "current": 71, "vibration": 1.4},
}


def generate_sensor_data(machine: Machine, drift: bool = False) -> SensorData:
    base = BASELINES.get(machine.machine_type.lower(), BASELINES["moteur"])
    temp_offset = random.uniform(-3, 3) + (random.uniform(5, 14) if drift else 0)
    vib_offset = random.uniform(-0.8, 0.8) + (random.uniform(2, 4) if drift else 0)
    pressure_offset = random.uniform(-0.5, 0.5) + (random.uniform(0.4, 1.2) if drift else 0)
    rpm_offset = random.uniform(-40, 40) - (random.uniform(60, 140) if drift else 0)
    current_offset = random.uniform(-3, 3) + (random.uniform(4, 10) if drift else 0)

    vibration = max(0.1, base["vibration"] + vib_offset)
    return SensorData(
        machine_id=machine.id,
        temperature=round(base["temperature"] + temp_offset, 2),
        vibration_x=round(vibration + random.uniform(-0.3, 0.3), 2),
        vibration_y=round(vibration + random.uniform(-0.3, 0.3), 2),
        vibration_z=round(vibration + random.uniform(-0.3, 0.3), 2),
        pressure=round(base["pressure"] + pressure_offset, 2),
        rpm=round(base["rpm"] + rpm_offset, 2),
        current=round(base["current"] + current_offset, 2),
    )
