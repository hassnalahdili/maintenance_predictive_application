MACHINE_TYPES = (
    "moteur",
    "pompe",
    "convoyeur",
    "compresseur",
    "ventilateur",
    "generateur",
    "broyeur",
    "four",
)

ROLE_ALIASES = {
    "admin": "admin",
    "technicien": "technicien",
    "technician": "technicien",
    "expert": "expert",
    "viewer": "viewer",
}

USER_ROLES = tuple(dict.fromkeys(ROLE_ALIASES.values()).keys())

RISK_LEVELS = ("normal", "low", "medium", "high", "critical")
ALERT_STATUSES = ("active", "acknowledged", "escalated")


def normalize_machine_type(machine_type: str) -> str:
    value = (machine_type or "").strip().lower()
    if value == "générateur":
        value = "generateur"
    if value == "furnace":
        value = "four"
    return value


def normalize_role(role: str) -> str:
    value = (role or "").strip().lower()
    return ROLE_ALIASES.get(value, value)
