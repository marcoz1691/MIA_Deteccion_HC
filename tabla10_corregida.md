# Tabla 10 corregida — solo con evidencia reproducible

Las cifras «99 expedientes / 413 páginas / 2 137 redacciones» no tienen respaldo en el repositorio y el lote no está disponible. Esto es lo que sí se puede sostener hoy.

---

## Tabla 10 — Componente de anonimización sobre capa de texto nativa (v2)

| Aspecto | Estado verificable |
|---|---|
| **Implementación** | Versionada en el repositorio (657 líneas). Cuatro vías de detección: tabular (geométrica), bloque de firma, título profesional y campo etiquetado, más reconocimiento de entidades nombradas opcional |
| **Vía tabular** | Celda situada bajo una cabecera de columna del formulario HCU; delimitación por punto medio hacia la cabecera vecina |
| **Vía de firma** | Fila de nombre cuya línea inferior es una credencial reconocida (MEDICINA GENERAL, ANESTESIOLOGÍA, CI:, SENESCYT) |
| **Vía de título** | Secuencia onomástica precedida de abreviatura profesional (Dr., Dra., Lcda., Md., Ing., Psic., Tlgo.) |
| **Vía de campo etiquetado** | Valor que sigue a una etiqueta con dos puntos (Paciente:, Médico tratante:, Acompañante:) |
| **Consolidación** | Descarta duplicados con solapamiento superior al 50 % del área menor |
| **Filtro de vocabulario clínico** | Evita redactar diagnósticos: en «PADRE: HIPERTENSIÓN ARTERIAL» no se detecta nombre |
| **Corrida de verificación** | 1 documento / 20 páginas / 3 184 palabras en capa de texto |
| **Residuos detectados** | 1 (vía de título, página 6) sobre la salida ya procesada por la versión con OCR |
| **Determinismo** | Reproducible ante idéntica entrada; sin dependencia de reconocimiento óptico |
| **Medición de exhaustividad** | Pendiente: requiere anotación manual de referencia sobre una submuestra |

---

## Párrafo que reemplaza §7.4.1 «Resultados de la fase actual»

> La versión sobre capa de texto nativa se verificó sobre el expediente de veinte páginas ya procesado por la versión con reconocimiento óptico, cuya capa de texto comprende 3 184 palabras. La ejecución identificó un residuo de nombre por la vía de título en la página 6, correspondiente a un identificador que la versión anterior no había enmascarado. El resultado, aunque de volumen reducido, documenta la complementariedad entre ambas versiones: la detección geométrica sobre el flujo de contenido alcanza posiciones que el reconocimiento óptico había omitido, y lo hace de forma determinista y sin el error de transcripción propio del reconocimiento.
>
> La ejecución sobre el subconjunto completo de expedientes exportados por el sistema de registro no se incorpora a este informe. El componente está implementado y versionado, e incluye la emisión de un reporte de auditoría sin contenido clínico, de modo que la corrida a escala queda planteada como verificación inmediata una vez habilitado el acceso al lote correspondiente bajo el protocolo de custodia vigente.

---

## Otras cuatro apariciones de las mismas cifras — hay que corregirlas

| Ubicación | Texto actual | Reemplazo |
|---|---|---|
| **Resumen** (p. 4) | «…se ejecutó sobre 99 expedientes reales (413 páginas) y aplicó 2 137 redacciones en 25 segundos, sin falsos positivos registrados sobre terminología clínica.» | «…se implementó y verificó sobre el expediente piloto, donde identificó un residuo de identificación no cubierto por la versión con reconocimiento óptico. Su ejecución a escala queda planteada como verificación inmediata.» |
| **Abstract** (p. 5) | «…a further set of 99 records (413 pages) processed by a second de-identification component… which applied 2,137 redactions with no false positives…» | «…and a second de-identification component operating on the native PDF text layer, verified on the pilot record, where it identified a residual identifier missed by the OCR-based version.» |
| **Conclusión 2** (p. 78) | «La segunda versión se ejerció sobre 99 expedientes reales (413 páginas), sobre los que aplicó 2 137 redacciones sin falsos positivos…» | «La segunda versión, orientada a expedientes con capa de texto nativa, se implementó y verificó sobre el expediente piloto, donde detectó un residuo de identificación no cubierto por la versión con reconocimiento óptico; su ejecución a escala y la medición de exhaustividad frente a una anotación de referencia permanecen pendientes.» |
| **§7.5.5** (p. 77) | «El volumen de material identificado efectivamente tratado asciende a 99 expedientes clínicos (413 páginas)…» | «El material identificado efectivamente tratado corresponde al expediente autorizado de veinte páginas, procesado de forma local por el módulo de anonimización, sin egreso hacia servicios de terceros y con los archivos originales excluidos del control de versiones conforme a las políticas descritas.» |

---

## Tabla 11 — un solo ajuste

La comparación conceptual entre v1 y v2 se sostiene tal como está: contrasta diseño, no volumen. Solo la última fila afirma más de lo demostrado.

| Dimensión | v1 — OCR | v2 — Capa de texto |
|---|---|---|
| Naturaleza del indicador | Estimación | **Medición directa sobre la capa de texto; la exhaustividad queda pendiente de contraste con anotación manual de referencia** |

---

## Lo que no se toca: la Tabla 9 sigue siendo tu evidencia fuerte

Verificada íntegramente contra `anonimizacion_agregados.json` y `verificacion_humana_resumen.json`:

| Métrica | Valor |
|---|---|
| Documentos / páginas | 1 / 20 |
| Hallazgos / cajas tachadas | 127 / 87 |
| Palabras reconocidas | 5 212 |
| Tiempo de procesamiento | 77,5 s |
| Confianza OCR (media / mín. / máx.) | 74,57 / 40,2 / 89,6 |
| Página a revisión | 10 (OCR 40,2) |
| Recall NOMBRE | 0,898 (115/128) |
| Recall CÉDULA / HC / DIRECCIÓN | 1,000 (10/10) · 1,000 (12/12) · 1,000 (1/1) |
| Criterio de bloqueo | No cumplido |
| Oraciones extraídas / omitidas | 96 / 13 |

Y un desglose por método de detección que hoy no reportas y refuerza el argumento de las cuatro capas:

| Origen del hallazgo | n |
|---|---|
| Contexto | 52 |
| NER | 43 |
| Celda | 12 |
| Etiqueta | 12 |
| Expresión regular | 8 |

---

## Por qué esto te conviene más que dejar las cifras sin respaldo

Una corrida pequeña y reproducible vale más que una grande que nadie puede verificar. Con este texto:

- El componente queda documentado como implementado y versionado, que es cierto y comprobable.
- La limitación se declara de forma expresa, en la misma línea que ya usas para el kappa y para la reducción del 50 % — y esa coherencia en reconocer límites es lo que el docente valoró.
- Desaparece el riesgo de que el tribunal pida reproducir una cifra que no existe.
