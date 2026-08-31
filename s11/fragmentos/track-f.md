# §6 Ética y privacidad

El proyecto trata dos fuentes de datos de naturaleza jurídica distinta, y esa distinción gobierna la
totalidad de las decisiones técnicas descritas en esta sección. MEDEC es un conjunto público de
investigación, en inglés, sin datos personales identificables, y sobre él se ejecutan el
entrenamiento, el ajuste y la publicación de métricas, con libertad para emplear servicios de
inferencia externos. El corpus de CITIMED, en cambio, está compuesto por historias clínicas reales
en español que contienen datos personales de salud, categoría que la Ley Orgánica de Protección de
Datos Personales del Ecuador califica como sensible y somete a base de licitud reforzada y a medidas
de seguridad proporcionales al riesgo. Para ese material el proyecto se impone una regla sin
excepciones: **ninguna nota clínica de CITIMED, ni original ni de-identificada, se transmite a un
servicio de inferencia externo**. Cuando el análisis requiere un modelo de lenguaje sobre datos con
información de salud, se emplea un modelo servido localmente mediante Ollama en
`http://localhost:11434/v1`; la ruta hacia API externa queda reservada al conjunto público.

## Protocolo de de-identificación

La de-identificación se ejecuta con un pipeline propio, desarrollado en `s11/anonimizador_ocr/`, que
rasteriza cada página del PDF escaneado, reconoce el texto con Tesseract en español, localiza los
identificadores y los **tacha a nivel de píxel**. El PDF de salida se reconstruye desde cero a
partir de las imágenes ya tachadas, de modo que no arrastra la capa de texto original, ni
anotaciones, ni adjuntos, ni metadatos de autor, fecha o software; cuando se solicita un PDF
buscable, la nueva capa de texto se genera con un segundo reconocimiento ejecutado sobre la imagen
ya redactada, por lo que no puede contener lo suprimido. Todo el proceso se ejecuta en local, sin
llamadas de red en ninguna etapa.

La detección se organiza en capas de dependencia decreciente respecto del reconocimiento óptico, un
diseño que responde directamente al hecho de que el OCR convencional lee bien lo impreso y mal la
escritura a mano. Las **reglas** cubren los identificadores estructurados; el **contexto y el
reconocimiento de entidades** con spaCy cubren los nombres en prosa; el **tachado junto a etiquetas**
aprovecha que la etiqueta impresa del formulario sí se lee aunque el valor manuscrito no; la
**máscara de tinta** decide la posición del valor observando los píxeles escritos y extiende la caja
siguiendo el trazo, lo que cubre manuscrito ilegible, celdas de tabla y bloques de firma; y las
**zonas fijas** por plantilla se tachan siempre, con independencia de lo que el OCR haya leído. Las
categorías redactadas son nombre, cédula, RUC, teléfono, correo electrónico, fecha de nacimiento,
número de historia clínica, dirección y edad de noventa años o más, además de las zonas fijas.

Como referencia metodológica se adoptan los dieciocho identificadores del método *Safe Harbor* de
HIPAA, no por aplicabilidad jurisdiccional —HIPAA no es derecho aplicable en Ecuador— sino porque
constituyen una lista de verificación reconocida y auditable. Sobre esa referencia se realiza la
adaptación al contexto ecuatoriano, que es la principal aportación local del pipeline: validación de
la cédula de identidad por código de provincia y **dígito verificador de módulo 10**, validación del
RUC como cédula de persona natural seguida de `001` o por forma para sociedades, reconocimiento del
formato de numeración telefónica nacional con prefijo `+593` opcional, y reconocimiento de las
denominaciones del número de historia clínica que circulan en el sistema de salud ecuatoriano
(`HCU`, `Historia Clínica Única`, `N° de Archivo`). Se añade una normalización de las confusiones
típicas del OCR sobre tokens numéricos, que preserva los desplazamientos de carácter para no
desalinear las cajas de píxeles.

Dos decisiones de criterio merecen justificación explícita. La primera es que **también se redactan
los nombres del personal sanitario**: son datos personales de personas físicas identificadas, no
amparados por la autorización relativa al material del paciente, y en una clínica de tamaño acotado
funcionan como cuasi-identificadores, porque combinados con la fecha de atención y la especialidad
reducen el conjunto de pacientes posibles a un número muy pequeño. La segunda es que **se redacta la
fecha de nacimiento y se conservan por defecto las fechas de atención**: la primera es un
identificador directo de alta capacidad de reidentificación y de valor analítico nulo para la tarea,
mientras que las segundas sostienen la coherencia temporal de la nota, que es precisamente el
material sobre el que se detectan inconsistencias. Esta segunda decisión constituye una desviación
consciente del *Safe Harbor* estricto, se declara como tal, y se compensa con el procesamiento local,
la exclusión del material identificable del control de versiones y la no cesión del corpus.

Sobre la historia clínica de veinte páginas autorizada por CITIMED, la corrida documentada produjo
**127 hallazgos distribuidos en las veinte páginas**. La categoría nombre aparece en 115 cajas, el
número de historia clínica en 11, la cédula en 10 y la dirección en 1; los totales suman más de 127
porque una misma caja puede fusionar categorías contiguas. Por capa de detección, el reparto fue
contexto 52, reconocimiento de entidades 43, celda de tabla 12, etiqueta de formulario 12 y reglas
8, un perfil coherente con el diseño: los identificadores estructurados son pocos y se concentran en
la cabecera, mientras que los nombres se dispersan por la prosa, las firmas y los campos de personal.
Una única página, la número 10, quedó derivada a revisión manual por confianza media de OCR de
**40,2 frente al umbral de 55**, con el motivo registrado como probable manuscrito.

## Autorización institucional

El tratamiento de la historia clínica empleada cuenta con **autorización institucional de CITIMED
para uso académico**, otorgada en el marco de este trabajo de titulación y sujeta a las condiciones
de de-identificación, custodia local y no cesión a terceros aquí descritas. La formalización
documental de esa autorización se encuentra pendiente de incorporación al expediente a la fecha de
esta versión del informe; el equipo se abstiene deliberadamente de consignar número de oficio, fecha
o firmante que no obren en su poder en forma verificable, y deja los campos correspondientes como
marcadores explícitos en el anexo ético. En consecuencia, ninguna afirmación de esta sección debe
leerse como constancia formal de aprobación: la autorización está declarada por el equipo y su
respaldo documental está en trámite. El material sintético incluido en el repositorio con fines de
prueba contiene datos íntegramente ficticios y no proviene de ninguna persona real.

## Cadena de custodia

El repositorio excluye por configuración todo el material identificable: las historias clínicas
originales, las imágenes de revisión —que muestran la página **sin tachar** con las cajas
superpuestas y son, por tanto, plenamente identificables—, los informes con texto detectado en claro
y el corpus anotado. Solo dos clases de artefacto abandonan el equipo de procesamiento: agregados sin
texto, es decir recuentos, distribuciones por categoría y por capa, métricas de confianza y listados
de páginas derivadas a revisión; y páginas ya tachadas y verificadas por doble revisor, cuando su
inclusión como evidencia visual resulta necesaria. Las cifras del apartado anterior pertenecen a la
primera clase. La trazabilidad se sostiene en los informes de hallazgos que cada corrida deja
localmente, y la verificación externa se habilita publicando **hashes** de los artefactos en lugar de
su contenido, lo que acredita la identidad del archivo auditado sin revelar nada de él.

El control de calidad no delega en el automatismo. Se revisa el **100 % de las páginas con doble
revisor** e integrante dirimente, sin muestreo, contrastando la imagen de revisión con la imagen
anonimizada; las páginas señaladas por baja confianza de OCR reciben inspección reforzada palabra por
palabra. Una página no se incorpora al corpus hasta que ambos revisores confirmen **recall del 100 %
en nombre, cédula y número de historia clínica**, las tres categorías de reidentificación directa e
inmediata en el contexto ecuatoriano, que concentran además la práctica totalidad de los hallazgos
observados. Ante discrepancia prevalece la lectura más conservadora. Cuando se detecta un escape, se
detiene el uso de la página, se corrige la causa en el pipeline —variante de etiqueta, zona fija,
segmentación, umbral— y se **reprocesa el lote completo**, no solo la página afectada, porque la
misma causa puede haber producido escapes no detectados en otras páginas.

## Límites declarados

El equipo declara sus limitaciones de forma explícita, por considerar que la descripción honesta de
las carencias es parte del rigor exigible. La más relevante es que **Tesseract tiene recall bajo
frente al manuscrito real**: las capas de etiquetas, tinta y zonas fijas existen para no depender del
reconocimiento del valor escrito a mano, pero su cobertura es posicional y funciona cuando el dato
está donde el formulario indica. Un nombre escrito a mano en medio de una nota de evolución, fuera de
cualquier campo etiquetado, **puede escaparse**; solo la revisión humana o la incorporación de un
modelo específico de manuscrito, ejecutable también en local, cubriría ese caso. El sistema está
calibrado para recall y no para precisión, de modo que produce **sobre-tachado** —etiquetas y
palabras contiguas redactadas—, coste que se acepta porque degrada la utilidad del corpus en lugar de
exponer a una persona. Las firmas, huellas, sellos, códigos de barras y fotografías no son texto y no
se detectan: dependen íntegramente de las zonas fijas por plantilla y del revisor. Persiste, por
último, un riesgo residual de reidentificación por inferencia, ya que una combinación suficientemente
específica de diagnóstico, procedimiento y fecha de atención puede singularizar a un paciente en una
clínica pequeña; se mitiga por la vía de la custodia y no por la supresión adicional de contenido
clínico, que destruiría la utilidad del material. Ninguna cifra de este informe debe interpretarse
como garantía de de-identificación completa: **la anonimización automática no sustituye la revisión
humana**, sino que reduce el volumen de trabajo manual y concentra la atención del revisor donde el
riesgo es mayor.

## Uso responsable

El sistema es un prototipo de investigación académica. No es un dispositivo médico, no ha sido
sometido a validación clínica prospectiva y no debe emplearse como soporte de decisiones
asistenciales. No diagnostica ni prescribe: señala oraciones cuya formulación resulta compatible con
una inconsistencia documental, lo cual es una afirmación sobre el texto y no sobre el paciente. La
responsabilidad clínica y legal permanece íntegramente en el profesional tratante, a quien una alerta
no exonera ni cuya ausencia exime de revisar el registro. El diseño privilegia deliberadamente la
localización —de ahí la reformulación de la tarea de nivel de nota a nivel de oración— para que cada
alerta sea verificable en segundos leyendo el fragmento señalado; sobre MEDEC, el sistema localiza
correctamente la oración errónea en el 84,6 % de las notas con error, 263 de 311, lo que implica que
ante una alerta dudosa el profesional debe leer la nota y no solo la oración. Las métricas a nivel de
oración, ROC-AUC de 0,949 y AUPRC de 0,419 sobre una prevalencia de 4,5 %, se reportan conjuntamente
para que la brecha entre ambas se lea como lo que es, la consecuencia esperada de una clase muy
minoritaria, y no como una promesa de precisión operativa. Estas cifras provienen de MEDEC, en inglés
y en dominio hospitalario general: **la transferencia al español odontológico está por medir**, y
medirla es la finalidad del corpus anotado con aval ético que esta sección habilita.

## Anexos

El desarrollo completo de lo aquí sintetizado se encuentra en dos anexos, cuyo contenido no se
reproduce en el cuerpo del informe:

| Anexo | Documento | Contenido |
|---|---|---|
| Anexo ético | `s11/docs/anexo_etico.md` | Marco normativo, correspondencia con los dieciocho identificadores de HIPAA, protocolo de de-identificación por capas y categorías, constancia de autorización institucional, cadena de custodia, control de calidad, límites y uso responsable |
| Guía de anotación | `s11/docs/guia_anotacion.md` | Definición operativa de inconsistencia clínica, tipos de error con ejemplos, unidad de anotación, esquema de datos, procedimiento de doble anotación con kappa de Cohen y reglas de casos límite |

La implementación del pipeline, sus parámetros y el procedimiento de instalación en un entorno sin
conexión se documentan en `s11/anonimizador_ocr/README.md`.
