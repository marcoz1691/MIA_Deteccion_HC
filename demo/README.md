# Demo interactiva — guion de 2 minutos

Para presentar al profesor con `streamlit run demo/app.py`.

## 1. Contexto (20 s)

> Detectamos inconsistencias clínicas **a nivel de oración**: no solo si la nota tiene error,
> sino **cuál oración** es sospechosa. Comparamos tres enfoques: léxico (TF-IDF),
> razonamiento semántico (LLM) y LLM anclado en guías clínicas (RAG).

## 2. Ejemplo con error de medicación (60 s)

1. En **Cargar ejemplo**, elegir *Error de medicación (alergia a penicilina)*.
2. Verificar banner verde: **Modo demo local — ningún dato sale del equipo**.
3. Clic en **Analizar nota**.
4. Mostrar la **oración más sospechosa** resaltada (amoxicilina pese a alergia).
5. Abrir la tabla: scores por brazo (ordenados por score).
6. Abrir expander **Contexto RAG** → fragmentos de medicación que justifican la alerta.

## 3. Comparación de brazos (30 s)

Ir a **Configuración** → desmarcar LLM y mostrar solo TF-IDF (rápido, local).
Volver a activar LLM + RAG (mock) y comparar scores en la tabla.

## 4. Evidencia cuantitativa (10 s)

Página **Métricas** → ROC-AUC 0.949, localización 84.6 % sobre MEDEC.

## Seguridad

- Mock LLM activo por defecto (no requiere internet ni API key).
- Al desactivar mock con API configurada: checkbox de consentimiento PHI obligatorio.
- Banner persistente indica modo local vs API externa.
- Auditoría en `salidas_s7/audit.log` (hash SHA-256, sin texto clínico).
- Si desactivas mock y la API no responde: **fallback automático a TF-IDF** con banner de alerta.

## Autenticación opcional

Copiar `.streamlit/secrets.toml.example` → `secrets.toml` y activar:

```toml
ENABLE_AUTH = true
AUTH_USERS = { medico = "tu_contraseña" }
```

## Requisitos

Instalación completa (clonar repo, venv, MEDEC, entrenar modelo): ver la sección **Inicio rápido** del [`README.md`](../README.md) en la raíz del proyecto.

Resumen mínimo:

```bash
python -m venv .venv && .venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try
python s6/modelo_ajustado.py
streamlit run demo/app.py
```

- Mock LLM activo por defecto (no requiere internet ni API key)

## Estructura UI

```
demo/
├── app.py              # Análisis (flujo principal)
├── pages/
│   ├── 1_Metricas.py
│   ├── 2_Acerca.py
│   └── 3_Configuracion.py
├── components/         # Design system y paneles
└── state.py            # Session state y cache
```
