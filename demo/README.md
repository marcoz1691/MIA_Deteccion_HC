# Demo interactiva — guion de 2 minutos

Para presentar al profesor con `streamlit run demo/app.py`.

## 1. Contexto (20 s)

> Detectamos inconsistencias clínicas **a nivel de oración**: no solo si la nota tiene error,
> sino **cuál oración** es sospechosa. Comparamos tres enfoques: léxico (TF-IDF),
> razonamiento semántico (LLM) y LLM anclado en guías clínicas (RAG).

## 2. Ejemplo con error de medicación (60 s)

1. En **Cargar ejemplo**, elegir *Error de medicación (alergia a penicilina)*.
2. Clic en **Analizar nota**.
3. Mostrar la **oración más sospechosa** resaltada (amoxicilina pese a alergia).
4. Abrir la tabla: scores por brazo.
5. Activar expander **Contexto RAG** → chunk de medicación que justifica la alerta.

## 3. Comparación de brazos (30 s)

En la sidebar, desmarcar LLM y mostrar solo TF-IDF (rápido, local).
Volver a activar LLM + RAG (mock) y comparar scores en la tabla.

## 4. Evidencia cuantitativa (10 s)

Sidebar → **Métricas de referencia S7**: AUC 0.949, localización 84.6 % sobre MEDEC.

## Requisitos

- Modelo entrenado: `python s6/modelo_ajustado.py`
- Mock LLM activo por defecto (no requiere internet ni API key)
