# Delimitación del alcance del detector — texto para el documento

**Problema:** el documento describe un detector de inconsistencias de propósito general, pero el detector implementado opera sobre **cuatro ejes** (lateralidad, sexo, alergias, edad) y excluye medicamentos de forma explícita. La restricción se lee en la **Figura 16 del propio documento** (*«Medicamentos aún no se evalúan»*) pero el texto nunca la enuncia.

**Riesgo:** un lector atento ve que la captura contradice al cuerpo. Y §1.1.2 sigue listando *«Prescripción de medicamentos no compatibles con alergias del paciente»* entre las inconsistencias objetivo.

**Evidencia en el repositorio:** `s7/prompts.py` (`EJES_MVP_ES` / `EJES_MVP_EN`), `s7/knowledge/mvp_consistencia.txt`, `s7/knowledge/medication_es.txt`, prueba `tests/s7/test_prompts_mvp.py`, commits `41fcc56` (2026-09-02) y `0be92db` (2026-09-03).

---

## Dato crítico de fechas — decide cómo lo declaras

| Hecho | Fecha |
|---|---|
| Evaluación tripartita reportada en la Tabla 8 (`metricas_llm_real.json`) | **2026-08-31** |
| Restricción MVP introducida en `s7/prompts.py` | **2026-09-02** |

**Las métricas del brazo generativo se calcularon con los prompts generales, dos días antes de que existiera la restricción.** Además, la caché de inferencia se indexa por SHA-256 del prompt, así que el cambio la invalidó: re-ejecutar `s11/eval_llm_real.py` hoy lanzaría 400 llamadas nuevas y daría cifras distintas.

No es un error mientras se declare. Es un error si no se declara y alguien intenta reproducirlo.

---

## 1. Nuevo apartado 7.2.7 — Alcance del detector

> Insertar antes de «Funcionamiento del prototipo». Numerar los siguientes en consecuencia.

### 7.2.7. Alcance del detector y ejes de inconsistencia evaluados

El motor de detección no opera sobre el universo completo de inconsistencias documentales, sino sobre un conjunto acotado de cuatro ejes verificables a partir del propio expediente, sin recurrir a conocimiento clínico externo:

1. **Lateralidad:** contraste entre el diagnóstico o el procedimiento y el examen físico, tanto en la parte anatómica como en el lado.
2. **Sexo del paciente:** contradicción entre el sexo declarado y una mención posterior, o entre el sexo y un procedimiento incompatible con él.
3. **Alergias frente a prescripciones:** indicación de un fármaco de la misma clase que una alergia documentada en la nota.
4. **Edad:** procedimientos o hallazgos incompatibles con la edad registrada, o edades discordantes entre dos evoluciones.

Los cuatro comparten una propiedad que sostiene la decisión: son **contradicciones internas del expediente**. Su verificación no exige un vademécum, una base de interacciones farmacológicas ni un modelo de razonamiento clínico; basta contrastar dos afirmaciones de la misma historia. Esa autocontención es lo que permite auditar cada alerta contra el texto y hace viable la supervisión humana.

Quedan **fuera del alcance de esta fase** los errores de medicación entendidos como dosis, duplicidad o suspensión temporal de un tratamiento habitual para un procedimiento, así como las discordancias de signos vitales, tolerancia oral, hemodinamia o indicaciones de egreso. La exclusión responde a una limitación de evidencia y no de arquitectura: detectar una dosis incorrecta exige una fuente posológica normalizada de la que el proyecto no dispone, y emitir alertas sin esa base produciría falsos positivos en un dominio donde la carga de revisión ya es el principal costo operativo. La contradicción entre una alergia documentada y una prescripción —el caso de medicación de mayor gravedad clínica— sí permanece en alcance, porque se resuelve dentro de la nota.

Esta delimitación es posterior a la evaluación comparativa sobre el corpus MEDEC reportada en el apartado 7.3 y no la afecta: las métricas de ese apartado corresponden a la tarea general de detección de errores definida por el propio corpus. La restricción a cuatro ejes gobierna el comportamiento del prototipo sobre expedientes de la Clínica CITIMED, y su verificación empírica se plantea entre las líneas de trabajo inmediato.

---

## 2. Nota al pie de la Tabla 8

> Añadir como nota al pie de la tabla, o como último párrafo del apartado 7.3.3.

> Las métricas del brazo generativo corresponden a la formulación de *prompt* vigente al 31 de agosto de 2026, de propósito general sobre los tipos de error definidos por MEDEC. Con posterioridad a esta evaluación, el *prompt* del prototipo se acotó a los cuatro ejes descritos en el apartado 7.2.7 para su operación sobre expedientes de CITIMED. Dado que la caché de inferencia se indexa por el hash del *prompt*, una reejecución con la formulación vigente no reproduce estas cifras: mediría una tarea distinta y más restringida. La conclusión arquitectónica —el esquema en cascada con el clasificador léxico como componente de producción— no se altera, puesto que se sustenta en la comparación bajo condiciones idénticas para los tres brazos.

---

## 3. Corrección en §1.1.2

En la lista de inconsistencias frecuentes, la viñeta *«Prescripción de medicamentos no compatibles con alergias del paciente»* **es correcta y se mantiene** (las alergias sí están en alcance). No requiere cambio.

Si el listado incluyera errores de dosis o duplicidad, esos sí deberían marcarse como fuera del alcance de la fase; en la redacción actual no aparecen.

---

## 4. Ajuste en las Conclusiones (§8.1)

> Añadir al final de la conclusión 1, después de «…fundamenta empíricamente la arquitectura en cascada adoptada».

> A esa decisión se suma una segunda delimitación, de alcance: el detector desplegado sobre expedientes institucionales opera sobre cuatro ejes de contradicción interna —lateralidad, sexo, alergias y edad—, verificables sin conocimiento clínico externo. Acotar el dominio antes que ampliarlo fue una elección deliberada frente al perfil de precisión observado, y define con claridad la superficie sobre la que el sistema puede responder.

---

## 5. Añadir a Trabajo futuro (§9)

> Como quinto punto, o dentro del punto 1.

> **5. Ampliación progresiva de los ejes de inconsistencia**
>
> El detector opera hoy sobre cuatro ejes de contradicción interna. Su ampliación admite dos rutas de distinto costo. La primera, de incorporación inmediata, es la **contradicción entre diagnósticos** dentro de un mismo episodio —dos diagnósticos primarios incompatibles entre evoluciones—, que conserva la propiedad de autocontención de los ejes actuales y cuya regla ya está formulada en la base de conocimiento del sistema. La segunda, de mayor alcance, son los **errores de medicación por dosis, duplicidad o interacción**, que exigen incorporar al índice vectorial una fuente posológica normalizada —vademécum institucional o cuadro nacional de medicamentos básicos— antes de poder emitir alertas con precisión aceptable.

---

## Verificación tras aplicar

- [ ] §7.2.7 existe y enuncia los cuatro ejes
- [ ] La Tabla 8 tiene la nota al pie con la fecha del *prompt*
- [ ] La Figura 16 ya no contradice al cuerpo: la captura dice «Medicamentos aún no se evalúan» y ahora §7.2.7 lo explica
- [ ] §8.1 menciona la delimitación
- [ ] §9 incluye la ruta de ampliación
- [ ] Buscar `medicamento` y `medicación` en el documento: cada aparición debe ser coherente con el alcance declarado
