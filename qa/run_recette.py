from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
PYTHON_EXE = ROOT_DIR / "pfe" / "Scripts" / "python.exe"
DEFAULT_PORT = 8010


@dataclass
class CaseResult:
    case_id: str
    requirement: str
    status: str
    duration_ms: int
    details: dict[str, Any]


class RecipeError(RuntimeError):
    pass


class RecipeRunner:
    def __init__(self, port: int, start_db: bool) -> None:
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.start_db = start_db
        self.results: list[CaseResult] = []
        self.backend_process: subprocess.Popen[str] | None = None
        self.db_started_by_runner = False

    def run(self) -> dict[str, Any]:
        self.ensure_prerequisites()
        self.ensure_database()
        self.start_backend()
        try:
            admin_auth = self.run_case("CA-05", "Authentification admin JWT", self.case_admin_login)
            dashboard_data = self.run_case("CA-01", "Dashboard et KPIs", lambda: self.case_dashboard(admin_auth["token"])) if admin_auth else None
            tech_data = self.run_case("OF-01A", "Creation utilisateur technicien", lambda: self.case_create_technician(admin_auth["token"])) if admin_auth else None
            tech_auth = self.run_case("OF-01B", "Connexion technicien", lambda: self.case_login(tech_data["email"], tech_data["password"])) if tech_data else None
            machine_data = self.run_case("CA-02", "CRUD machines complet", lambda: self.case_machine_flow(admin_auth["token"], tech_auth["token"])) if admin_auth and tech_auth else None
            if admin_auth and machine_data:
                self.run_case("CA-06", "Regles metier", lambda: self.case_rule_flow(admin_auth["token"], machine_data["reference_machine_id"]))
                self.run_case("CA-07", "Predictions par machine", lambda: self.case_predictions(admin_auth["token"], machine_data["reference_machine_id"]))
                self.run_case("CP-02", "Temps de reponse prediction < 200 ms", lambda: self.case_prediction_performance(admin_auth["token"], machine_data["reference_machine_id"]))
            else:
                self.add_skipped_case("CA-06", "Regles metier", "Prerequis admin ou machine indisponibles")
                self.add_skipped_case("CA-07", "Predictions par machine", "Prerequis admin ou machine indisponibles")
                self.add_skipped_case("CP-02", "Temps de reponse prediction < 200 ms", "Prerequis admin ou machine indisponibles")

            if admin_auth and tech_auth and machine_data:
                self.run_case("CA-03", "Generation des alertes", lambda: self.case_alert_flow(admin_auth["token"], tech_auth["token"], machine_data["reference_machine_id"]))
            else:
                self.add_skipped_case("CA-03", "Generation des alertes", "Prerequis admin, technicien ou machine indisponibles")

            if admin_auth:
                self.run_case("OF-05", "Audit et traces de securite", lambda: self.case_audit_logs(admin_auth["token"]))
            else:
                self.add_skipped_case("OF-05", "Audit et traces de securite", "Connexion admin indisponible")

            if admin_auth and tech_data:
                self.run_case("OF-01C", "Suppression utilisateur", lambda: self.case_delete_technician(admin_auth["token"], tech_data["user_id"]))
            else:
                self.add_skipped_case("OF-01C", "Suppression utilisateur", "Utilisateur technicien non cree")

            self.add_manual_cases(dashboard_data.get("available_sites", []) if dashboard_data else [])
        finally:
            self.stop_backend()
            self.stop_database_if_needed()

        summary = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "base_url": self.base_url,
            "results": [asdict(result) for result in self.results],
            "counts": {
                "pass": sum(1 for result in self.results if result.status == "PASS"),
                "fail": sum(1 for result in self.results if result.status == "FAIL"),
                "skip": sum(1 for result in self.results if result.status == "SKIP"),
                "manual": sum(1 for result in self.results if result.status == "MANUAL"),
            },
        }
        return summary

    def ensure_prerequisites(self) -> None:
        if not PYTHON_EXE.exists():
            raise RecipeError(f"Python du projet introuvable: {PYTHON_EXE}")
        if self._is_port_open("127.0.0.1", self.port):
            raise RecipeError(f"Le port {self.port} est deja utilise.")

    def ensure_database(self) -> None:
        if self._is_port_open("127.0.0.1", 5432):
            return
        if not self.start_db:
            raise RecipeError("PostgreSQL n'est pas accessible sur localhost:5432. Relancez avec --start-db ou demarrez la base.")

        self._run_command(["docker", "compose", "up", "-d", "db"], cwd=ROOT_DIR)
        self.db_started_by_runner = True
        deadline = time.time() + 60
        while time.time() < deadline:
            if self._is_port_open("127.0.0.1", 5432):
                return
            time.sleep(1)
        raise RecipeError("La base PostgreSQL n'a pas demarre dans le delai imparti.")

    def stop_database_if_needed(self) -> None:
        if self.db_started_by_runner:
            self._run_command(["docker", "compose", "stop", "db"], cwd=ROOT_DIR, check=False)

    def start_backend(self) -> None:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        self.backend_process = subprocess.Popen(
            [str(PYTHON_EXE), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        deadline = time.time() + 60
        last_error = "Aucune reponse"
        while time.time() < deadline:
            if self.backend_process.poll() is not None:
                output = self.backend_process.stdout.read() if self.backend_process.stdout else ""
                raise RecipeError(f"Le backend s'est arrete pendant le demarrage.\n{output}")
            try:
                response = self.request("GET", "/", expected_status=200)
                if response.get("message"):
                    return
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                time.sleep(1)
        raise RecipeError(f"Le backend n'a pas repondu dans le delai imparti. Derniere erreur: {last_error}")

    def stop_backend(self) -> None:
        if not self.backend_process:
            return
        if self.backend_process.poll() is None:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
        self.backend_process = None

    def run_case(self, case_id: str, requirement: str, callback):
        started = time.perf_counter()
        try:
            details = callback()
            status = "PASS"
        except Exception as exc:  # noqa: BLE001
            details = {"error": str(exc)}
            status = "FAIL"
        duration_ms = int((time.perf_counter() - started) * 1000)
        result = CaseResult(
            case_id=case_id,
            requirement=requirement,
            status=status,
            duration_ms=duration_ms,
            details=self.sanitize_details(details if isinstance(details, dict) else {"value": details}),
        )
        self.results.append(result)
        return details if status == "PASS" else None

    def add_skipped_case(self, case_id: str, requirement: str, reason: str) -> None:
        self.results.append(
            CaseResult(
                case_id=case_id,
                requirement=requirement,
                status="SKIP",
                duration_ms=0,
                details={"reason": reason},
            )
        )

    def add_manual_cases(self, available_sites: list[str]) -> None:
        manual_cases = [
            (
                "CP-01",
                "Temps de chargement dashboard < 2 s",
                {
                    "mode": "manual",
                    "method": "Mesurer dans le navigateur avec DevTools sur / et verifier le chargement initial.",
                    "target": "< 2 s",
                },
            ),
            (
                "CP-03",
                "Concurrence 50 utilisateurs",
                {
                    "mode": "manual",
                    "method": "Executer un test de charge externe sur /api/dashboard/summary et /api/predictions/simulate/{machine_id}.",
                    "target": "Pas de degradation visible a 50 utilisateurs",
                },
            ),
            (
                "OT-03",
                "Rappel modele >= 80 %",
                {
                    "mode": "manual",
                    "method": "Evaluer le modele sur un jeu de verite terrain et calculer recall, precision, F1 et AUC.",
                    "target": "recall >= 0.80",
                },
            ),
            (
                "OT-04",
                "Anticipation moyenne >= 7 jours",
                {
                    "mode": "manual",
                    "method": "Comparer expected_failure_date aux dates reelles de panne sur un jeu de validation.",
                    "target": ">= 7 jours",
                },
            ),
            (
                "UI-RESP",
                "Interface responsive",
                {
                    "mode": "manual",
                    "method": "Verifier les ecrans Dashboard, Machines, Regles et Alertes en largeur mobile et desktop.",
                    "sites_hint": available_sites,
                },
            ),
            (
                "NAV-BROWSERS",
                "Compatibilite navigateurs",
                {
                    "mode": "manual",
                    "method": "Tester Chrome, Firefox, Edge et Safari sur connexion, dashboard, CRUD machines, regles et alertes.",
                },
            ),
        ]
        for case_id, requirement, details in manual_cases:
            self.results.append(
                CaseResult(
                    case_id=case_id,
                    requirement=requirement,
                    status="MANUAL",
                    duration_ms=0,
                    details=details,
                )
            )

    def case_admin_login(self) -> dict[str, Any]:
        return self.case_login("admin@example.com", "Admin123!")

    def case_login(self, email: str, password: str) -> dict[str, Any]:
        response = self.request("POST", "/api/auth/login", payload={"email": email, "password": password}, expected_status=200)
        token = response.get("access_token")
        user = response.get("user", {})
        if not token:
            raise RecipeError("Token JWT absent de la reponse de connexion.")
        return {"token": token, "user": user}

    def case_dashboard(self, admin_token: str) -> dict[str, Any]:
        response = self.request("GET", "/api/dashboard/summary", token=admin_token, expected_status=200)
        required_keys = {"total_machines", "active_alerts", "machines_at_risk", "status_distribution", "prediction_trend", "machine_health"}
        missing_keys = required_keys - set(response)
        if missing_keys:
            raise RecipeError(f"Dashboard incomplet, cles manquantes: {sorted(missing_keys)}")
        if response["total_machines"] < 1:
            raise RecipeError("Le dashboard ne retourne aucune machine.")
        return {
            "total_machines": response["total_machines"],
            "available_sites": response.get("available_sites", []),
            "available_types": response.get("available_types", []),
        }

    def case_create_technician(self, admin_token: str) -> dict[str, Any]:
        suffix = int(time.time())
        email = f"qa.technicien.{suffix}@example.com"
        password = "TechPass123"
        response = self.request(
            "POST",
            "/api/users/",
            token=admin_token,
            payload={
                "full_name": f"QA Technicien {suffix}",
                "email": email,
                "password": password,
                "role": "technicien",
            },
            expected_status=200,
        )
        return {"user_id": response["id"], "email": email, "password": password}

    def case_machine_flow(self, admin_token: str, tech_token: str) -> dict[str, Any]:
        machines = self.request("GET", "/api/machines/", token=admin_token, expected_status=200)
        moteur_machine = next((machine for machine in machines if machine["machine_type"] == "moteur"), None)
        if not moteur_machine:
            raise RecipeError("Aucune machine moteur disponible pour les tests.")

        suffix = int(time.time())
        created_machine = self.request(
            "POST",
            "/api/machines/",
            token=tech_token,
            payload={
                "name": f"QA Machine {suffix}",
                "machine_type": "moteur",
                "site": "Site QA",
                "status": "healthy",
                "notes": "cree depuis la recette automatisee",
            },
            expected_status=200,
        )

        updated_machine = self.request(
            "PUT",
            f"/api/machines/{created_machine['id']}",
            token=admin_token,
            payload={
                "name": created_machine["name"],
                "machine_type": created_machine["machine_type"],
                "site": "Site QA",
                "status": "medium",
                "notes": "mise a jour recette",
            },
            expected_status=200,
        )
        if updated_machine["status"] != "medium":
            raise RecipeError("La mise a jour de la machine n'a pas ete prise en compte.")

        detail = self.request("GET", f"/api/machines/{created_machine['id']}", token=admin_token, expected_status=200)
        for key in ("sensor_history", "prediction_history", "alert_history"):
            if key not in detail:
                raise RecipeError(f"Le detail machine ne contient pas {key}.")

        self.request("DELETE", f"/api/machines/{created_machine['id']}", token=admin_token, expected_status=200)
        remaining = self.request("GET", "/api/machines/", token=admin_token, expected_status=200)
        if any(machine["id"] == created_machine["id"] for machine in remaining):
            raise RecipeError("La suppression logique de la machine n'est pas effective.")

        return {"reference_machine_id": moteur_machine["id"], "created_machine_id": created_machine["id"]}

    def case_rule_flow(self, admin_token: str, machine_id: int) -> dict[str, Any]:
        suffix = int(time.time())
        rule = self.request(
            "POST",
            "/api/rules/",
            token=admin_token,
            payload={
                "name": f"QA Rule {suffix}",
                "machine_type": "moteur",
                "metric": "temperature",
                "operator": ">",
                "threshold": 110,
                "duration_seconds": 30,
                "severity": "high",
                "confidence": 0.95,
            },
            expected_status=200,
        )

        self.request(
            "POST",
            "/api/sensors/ingest",
            token=admin_token,
            payload={
                "machine_id": machine_id,
                "temperature": 120,
                "vibration_x": 4.5,
                "vibration_y": 4.4,
                "vibration_z": 4.3,
                "pressure": 8.2,
                "rpm": 1280,
                "current": 67,
            },
            expected_status=200,
        )

        simulation = self.request("GET", f"/api/rules/{rule['id']}/simulate?machine_id={machine_id}", token=admin_token, expected_status=200)
        if simulation["matched_records"] < 1:
            raise RecipeError("La simulation de regle ne detecte aucun enregistrement correspondant.")

        toggled = self.request("POST", f"/api/rules/{rule['id']}/toggle", token=admin_token, expected_status=200)
        if toggled["is_active"] is not False:
            raise RecipeError("La desactivation de la regle a echoue.")

        versions = self.request("GET", f"/api/rules/{rule['id']}/versions", token=admin_token, expected_status=200)
        if len(versions) < 2:
            raise RecipeError("Le versioning de la regle est incomplet.")
        return {"rule_id": rule["id"], "versions": len(versions)}

    def case_alert_flow(self, admin_token: str, tech_token: str, machine_id: int) -> dict[str, Any]:
        self.request(
            "POST",
            "/api/sensors/ingest",
            token=admin_token,
            payload={
                "machine_id": machine_id,
                "temperature": 125,
                "vibration_x": 6.0,
                "vibration_y": 6.1,
                "vibration_z": 6.2,
                "pressure": 8.5,
                "rpm": 1200,
                "current": 72,
            },
            expected_status=200,
        )

        alerts = self.request("GET", f"/api/alerts/?machine_id={machine_id}", token=admin_token, expected_status=200)
        if not alerts:
            raise RecipeError("Aucune alerte n'a ete generee apres ingestion critique.")
        latest_alert = alerts[0]
        if latest_alert["status"] not in {"active", "escalated", "acknowledged"}:
            raise RecipeError("Le statut d'alerte est invalide.")

        acknowledged = self.request(
            "POST",
            f"/api/alerts/{latest_alert['id']}/acknowledge",
            token=tech_token,
            payload={"comment": "prise en charge recette auto"},
            expected_status=200,
        )
        if acknowledged["status"] != "acknowledged":
            raise RecipeError("L'accuse de reception n'a pas mis a jour le statut de l'alerte.")
        return {"alert_id": latest_alert["id"], "status": acknowledged["status"]}

    def case_predictions(self, admin_token: str, machine_id: int) -> dict[str, Any]:
        simulation = self.request(
            "POST",
            f"/api/predictions/simulate/{machine_id}?drift=true&persist=true",
            token=admin_token,
            expected_status=200,
        )
        prediction = simulation.get("prediction", {})
        if prediction.get("alert_level") not in {"normal", "low", "medium", "high", "critical"}:
            raise RecipeError("La prediction simulee ne retourne pas de niveau de risque exploitable.")

        predictions = self.request("GET", f"/api/predictions/?machine_id={machine_id}", token=admin_token, expected_status=200)
        if not predictions:
            raise RecipeError("Aucune prediction historisee pour la machine testee.")
        return {"prediction_count": len(predictions), "latest_level": predictions[0]["alert_level"]}

    def case_audit_logs(self, admin_token: str) -> dict[str, Any]:
        logs = self.request("GET", "/api/audit-logs/", token=admin_token, expected_status=200)
        if not logs:
            raise RecipeError("Aucun log d'audit disponible.")
        interesting_actions = {"login_success", "create_user", "create_machine", "acknowledge_alert"}
        seen_actions = {log["action"] for log in logs}
        missing = sorted(interesting_actions - seen_actions)
        if missing:
            raise RecipeError(f"Logs d'audit incomplets, actions manquantes: {missing}")
        return {"log_count": len(logs)}

    def case_delete_technician(self, admin_token: str, user_id: int) -> dict[str, Any]:
        self.request("DELETE", f"/api/users/{user_id}", token=admin_token, expected_status=200)
        users = self.request("GET", "/api/users/", token=admin_token, expected_status=200)
        if any(user["id"] == user_id for user in users):
            raise RecipeError("La suppression utilisateur n'a pas ete prise en compte.")
        return {"deleted_user_id": user_id}

    def case_prediction_performance(self, admin_token: str, machine_id: int) -> dict[str, Any]:
        durations = []
        for _ in range(5):
            started = time.perf_counter()
            self.request(
                "POST",
                f"/api/predictions/simulate/{machine_id}?drift=false&persist=true",
                token=admin_token,
                expected_status=200,
            )
            durations.append((time.perf_counter() - started) * 1000)
        average_duration = round(sum(durations) / len(durations), 2)
        if average_duration >= 200:
            raise RecipeError(f"Temps moyen de prediction trop eleve: {average_duration} ms")
        return {"average_duration_ms": average_duration, "samples_ms": [round(item, 2) for item in durations]}

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        payload: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8")
                if response.status != expected_status:
                    raise RecipeError(f"{method} {path} a retourne {response.status} au lieu de {expected_status}")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RecipeError(f"{method} {path} a retourne HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RecipeError(f"Echec appel HTTP {method} {path}: {exc}") from exc

    @staticmethod
    def sanitize_details(details: Any) -> Any:
        if isinstance(details, dict):
            sanitized = {}
            for key, value in details.items():
                if key.lower() in {"token", "access_token", "password", "hashed_password"}:
                    sanitized[key] = "***redacted***"
                else:
                    sanitized[key] = RecipeRunner.sanitize_details(value)
            return sanitized
        if isinstance(details, list):
            return [RecipeRunner.sanitize_details(item) for item in details]
        return details

    @staticmethod
    def _is_port_open(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex((host, port)) == 0

    @staticmethod
    def _run_command(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        if check and completed.returncode != 0:
            raise RecipeError(
                f"Commande echouee ({' '.join(command)}).\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner de recette pour predictive_maintenance_app")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port temporaire du backend local")
    parser.add_argument("--start-db", action="store_true", help="Demarre docker compose db si PostgreSQL n'est pas disponible")
    parser.add_argument("--output", type=Path, default=None, help="Fichier JSON de sortie")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = RecipeRunner(port=args.port, start_db=args.start_db)
    try:
        report = runner.run()
    except RecipeError as exc:
        print(f"[RECETTE] ECHEC: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"[RECETTE] Rapport ecrit dans {args.output}")
    else:
        print(rendered)
    return 1 if report["counts"]["fail"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
