"""Prueba unitaria rápida del historial SQLite."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from api.db import HistorialDB


class TestHistorialDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = HistorialDB(Path(self.tmp.name) / "test.db", max_items=3)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_list_delete(self):
        r1 = {"top1": {"alerta": True}, "oraciones": []}
        saved = self.db.save_analisis(
            nota="Nota A",
            resultado=r1,
            ejemplo_id="propia",
            idioma="spanish",
            mock_llm=False,
            alerta=True,
        )
        self.assertTrue(saved["id"])
        items = self.db.list_analisis()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["nota"], "Nota A")
        self.assertTrue(self.db.delete_analisis(saved["id"]))
        self.assertEqual(self.db.count(), 0)

    def test_trim_max_items(self):
        for i in range(5):
            self.db.save_analisis(
                nota=f"Nota {i}",
                resultado={"oraciones": [], "top1": None},
            )
        self.assertLessEqual(self.db.count(), 3)


if __name__ == "__main__":
    unittest.main()
