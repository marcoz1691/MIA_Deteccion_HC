"""Fase 4/5 — Locust load/stress tests (TC-PERF, TC-STR).

Uso:
  locust -f tests/perf/locustfile.py --host=http://127.0.0.1:8000

Escenarios:
  TC-STR-01: Ramp-up 1→50 users, 5 min (web UI o --users 50 --spawn-rate 10)
  TC-STR-02: Spike (--users 100 --spawn-rate 100 -t 1m)
  TC-STR-03: Soak (--users 20 --spawn-rate 2 -t 2h)
  TC-STR-04: Payload grande (NotaLargaUser)
"""
from __future__ import annotations

import json
import os

from locust import HttpUser, between, task

NOTA_LIMPIA = (
    "Paciente de 45 años acude por control periodontal rutinario. "
    "Examen: encías rosadas, sin sangrado al sondaje. "
    "Plan: profilaxis y control en 6 meses."
)

NOTA_MEDICACION = (
    "Paciente refiere dolor en molar 36 desde hace 3 días. "
    "Antecedentes: alergia documentada a penicilina. "
    "Se indica amoxicilina 500 mg cada 8 h."
)

NOTA_GRANDE = ". ".join(
    [f"Oración número {i} sin inconsistencia aparente en evaluación clínica." for i in range(1, 501)]
) + "."


class ApiUser(HttpUser):
    """TC-STR-01/02/03: Carga estándar POST /generar."""

    wait_time = between(0.5, 2.0)

    @task(3)
    def generar_medicacion(self):
        self.client.post(
            "/generar",
            data=json.dumps(
                {
                    "nota_clinica": NOTA_MEDICACION,
                    "mock_llm": True,
                    "brazos": ["llm_zero"],
                    "umbral": 0.5,
                }
            ),
            headers={"Content-Type": "application/json"},
            name="/generar [medicacion]",
        )

    @task(2)
    def generar_limpia(self):
        self.client.post(
            "/generar",
            data=json.dumps(
                {
                    "nota_clinica": NOTA_LIMPIA,
                    "mock_llm": True,
                    "brazos": ["llm_zero"],
                    "umbral": 0.5,
                }
            ),
            headers={"Content-Type": "application/json"},
            name="/generar [limpia]",
        )

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")


class NotaLargaUser(HttpUser):
    """TC-STR-04: Payload grande (500 oraciones)."""

    wait_time = between(2, 5)

    @task
    def generar_nota_grande(self):
        with self.client.post(
            "/generar",
            data=json.dumps(
                {
                    "nota_clinica": NOTA_GRANDE,
                    "mock_llm": True,
                    "brazos": ["llm_zero"],
                    "umbral": 0.5,
                }
            ),
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/generar [nota_grande]",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return
            data = resp.json()
            if not data.get("truncado"):
                resp.failure("truncado=false esperado")


class TfidfOnlyUser(HttpUser):
    """TC-PERF-01/02: Solo TF-IDF para baseline de latencia."""

    wait_time = between(0.1, 0.5)

    @task
    def generar_tfidf(self):
        self.client.post(
            "/generar",
            data=json.dumps(
                {
                    "nota_clinica": NOTA_LIMPIA,
                    "mock_llm": True,
                    "brazos": ["tfidf"],
                    "umbral": 0.5,
                }
            ),
            headers={"Content-Type": "application/json"},
            name="/generar [tfidf]",
        )
