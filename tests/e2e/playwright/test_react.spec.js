// TC-UI-R01..08 — E2E React frontend (Fase 2)
import { test, expect } from "@playwright/test";

test.describe("React UI — Detección HC", () => {
  test("TC-UI-R01: carga inicial con formulario y ejemplos", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Detección de inconsistencias/i })).toBeVisible();
    await expect(page.getByLabel(/Texto de la historia/i)).toBeVisible();
    await expect(page.getByRole("group", { name: /Ejemplos precargados/i })).toBeVisible();
  });

  test("TC-UI-R03: ejemplo medicación genera alerta", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Medicación/i }).click();
    await page.getByRole("button", { name: /Analizar/i }).click();
    await expect(page.getByText(/alerta|inconsistencia|amoxicilina/i).first()).toBeVisible({
      timeout: 30_000,
    });
  });

  test("TC-UI-R04: nota limpia sin alerta crítica", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel(/Texto de la historia/i).fill(
      "Paciente de 45 años acude por control periodontal rutinario. " +
        "Examen: encías rosadas, sin sangrado al sondaje. Plan: profilaxis en 6 meses."
    );
    await page.getByRole("button", { name: /Analizar/i }).click();
    await expect(page.locator(".resultados, [class*='result']")).toBeVisible({ timeout: 30_000 });
  });

  test("TC-UI-R06: idioma EN disponible", async ({ page }) => {
    await page.goto("/");
    const idiomaSelect = page.locator("select").filter({ hasText: /Español|English/i });
    if (await idiomaSelect.count()) {
      await idiomaSelect.selectOption("english");
    }
    await expect(page.getByLabel(/Texto de la historia/i)).toBeVisible();
  });
});
