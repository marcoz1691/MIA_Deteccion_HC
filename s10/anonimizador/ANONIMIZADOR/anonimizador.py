"""
anonimizador.py
---------------
Anonimizador de historias clínicas (texto y PDF) para el proyecto CITIMED.
Implementa el "Servicio de Anonimización (②)" de la arquitectura del proyecto.

Enfoque HÍBRIDO (recomendado por la literatura de de-identificación):
    1) REGLAS  (reglas_ec.py): identificadores estructurados de Ecuador con alta
       precisión (cédula con dígito verificador, RUC, teléfono, email, fechas,
       nº de historia/IESS, edad >= 90, URL/IP).
    2) NER      (spaCy es_core_news_md, opcional): nombres de personas (PER),
       lugares (LOC) y organizaciones (ORG) que las reglas no pueden capturar.

Tratamiento del PHI:
    - Pseudonimización CONSISTENTE: cada entidad única recibe una etiqueta estable
      ([PACIENTE_1], [MEDICO_2], [LUGAR_1]...), de modo que la misma persona conserva
      la misma etiqueta en todo el documento (preserva coherencia clínica).
    - Fechas: se DESPLAZAN un offset constante por documento (no se borran), para
      preservar los intervalos entre eventos —esencial para detectar inconsistencias
      temporales— sin revelar las fechas reales.
    - Auditoría: se registra el CONTEO por tipo y un hash salado de cada valor
      (NUNCA el valor en claro), para no crear un segundo archivo con PHI.

IMPORTANTE (ética y seguridad):
    - La de-identificación automática NO es perfecta. Este servicio REDUCE el riesgo,
      no lo elimina. Se recomienda revisión humana por muestreo antes de liberar datos.
    - Por defecto es IRREVERSIBLE (anonimización). No se guarda un mapa de
      re-identificación. Si se necesita seudonimización reversible, debe cifrarse
      el mapa y custodiarse por separado (no incluido por diseño).

Uso:
    python anonimizador.py --entrada historia.txt   --salida salidas/
    python anonimizador.py --entrada historia.pdf   --salida salidas/
    python anonimizador.py --entrada carpeta/        --salida salidas/   # lote
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import random
import re
from pathlib import Path

import reglas_ec

# spaCy es opcional: si no está el modelo, se usa solo reglas + heurística de nombres
try:
    import spacy
    _NLP = spacy.load("es_core_news_md")
except Exception:  # pragma: no cover
    _NLP = None

SALT_POR_DEFECTO = "citimed-anon-v1"

# Honoríficos para clasificar personas y para heurística sin spaCy
_HON_MEDICO = re.compile(r"\b(dr|dra|dres|doctor|doctora|md|lic|lcda)\.?\s+", re.I)
_HON_PACIENTE = re.compile(r"\b(paciente|sr|sra|srta|don|do[ñn]a)\.?\s+", re.I)

# Etiquetas de campo y términos clínicos que NUNCA deben tratarse como identificadores,
# aunque el NER los marque (evita redactar "Paciente", "Nombre", "Diagnóstico"...).
_STOP = {
    "paciente", "nombre", "apellido", "apellidos", "medico", "médico", "doctor",
    "doctora", "responsable", "datos", "historia", "clinica", "clínica", "ingreso",
    "alta", "evolucion", "evolución", "diagnostico", "diagnóstico", "tratamiento",
    "motivo", "consulta", "antecedentes", "sexo", "edad", "direccion", "dirección",
    "correo", "telefono", "teléfono", "cedula", "cédula", "afiliacion", "afiliación",
    "esposa", "esposo", "hijo", "hija", "madre", "padre", "familiar", "iess",
    "citimed", "hospital", "clinica citimed", "servicio", "control", "indicaciones",
}
_PALABRAS_COMUNES = _STOP | {
    "av", "avenida", "calle", "y", "de", "del", "la", "el", "los", "las", "con",
    "por", "para", "mg", "cada", "horas", "dias", "días", "años",
    "dr", "dra", "dres", "doctor", "doctora", "sr", "sra", "srta", "don", "lic", "lcda",
}
# honorífico al inicio de una entidad PER (para despojarlo del nombre)
_HON_INICIO = re.compile(r"^(dr|dra|dres|doctor|doctora|md|lic|lcda|sr|sra|srta|don|do[ñn]a)\.?\s+", re.I)
# Heurística de nombre propio (2-3 palabras capitalizadas) para el modo sin spaCy
_NOMBRE_HEUR = re.compile(
    r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b")


class Anonimizador:
    def __init__(self, salt: str = SALT_POR_DEFECTO, desplazar_fechas: bool = True,
                 usar_ner: bool = True):
        self.salt = salt
        self.desplazar_fechas = desplazar_fechas
        self.usar_ner = usar_ner and (_NLP is not None)

    # --- utilidades ---
    def _hash(self, valor: str) -> str:
        return hashlib.sha256((self.salt + "|" + valor.lower()).encode()).hexdigest()[:12]

    def _offset_dias(self, doc_id: str) -> int:
        """Offset determinista por documento (mismo doc -> mismo desplazamiento)."""
        h = int(hashlib.sha256((self.salt + doc_id).encode()).hexdigest(), 16)
        rng = random.Random(h)
        # entre 31 y 365 días, con signo aleatorio; evita 0 para siempre alterar
        return rng.choice([-1, 1]) * rng.randint(31, 365)

    # --- detección de nombres/lugares ---
    def _limpiar_span(self, texto, ini, fin):
        """Recorta un span de entidad: elimina bordes no alfabéticos y descarta
           si el contenido es una etiqueta de campo o palabra común."""
        s = texto[ini:fin]
        # recortar espacios y signos de puntuación en los extremos
        izq = len(s) - len(s.lstrip(" \t:.-,;")); s2 = s.lstrip(" \t:.-,;")
        der = len(s2) - len(s2.rstrip(" \t:.-,;")); s2 = s2.rstrip(" \t:.-,;")
        ini2, fin2 = ini + izq, fin - der
        if fin2 - ini2 < 3:
            return None
        if s2.strip().lower() in _STOP:
            return None
        return ini2, fin2, s2

    def _entidades_ner(self, texto: str):
        """Ejecuta el NER LÍNEA POR LÍNEA para impedir que una entidad cruce saltos
           de línea (evita fusiones tipo 'López\\nMotivo')."""
        ents = []
        offset = 0
        for linea in texto.splitlines(keepends=True):
            contenido = linea.rstrip("\n")
            if contenido.strip():
                if self.usar_ner:
                    for e in _NLP(contenido).ents:
                        if e.label_ in ("PER", "LOC", "ORG"):
                            ini_g, fin_g = offset + e.start_char, offset + e.end_char
                            # despojar honorífico inicial de nombres de persona
                            if e.label_ == "PER":
                                mh = _HON_INICIO.match(texto[ini_g:fin_g])
                                if mh:
                                    ini_g += mh.end()
                            r = self._limpiar_span(texto, ini_g, fin_g)
                            if r:
                                ents.append({"inicio": r[0], "fin": r[1],
                                             "texto": r[2], "tipo": e.label_})
                else:
                    for rx in (_HON_MEDICO, _HON_PACIENTE):
                        for m in rx.finditer(contenido):
                            nm = _NOMBRE_HEUR.match(contenido[m.end():])
                            if nm:
                                ini = offset + m.end()
                                ents.append({"inicio": ini, "fin": ini + nm.end(),
                                             "texto": nm.group(), "tipo": "PER"})
            offset += len(linea)
        return ents

    def _propagar_partes_nombre(self, texto: str, per_textos):
        """Dado el conjunto de nombres de persona detectados, redacta también las
           MENCIONES SUELTAS de sus partes (p. ej. 'López' tras 'María López').
           Mejora el recall sin depender de que el NER reencuentre el apellido."""
        partes = set()
        for nombre in per_textos:
            for tok in re.split(r"\s+", nombre):
                tok = tok.strip(".,;:")
                if len(tok) >= 3 and tok[0].isupper() and tok.lower() not in _PALABRAS_COMUNES:
                    partes.add(tok)
        extra = []
        for tok in sorted(partes, key=len, reverse=True):
            for m in re.finditer(r"(?<![\wÁÉÍÓÚÑáéíóúñ])" + re.escape(tok) +
                                 r"(?![\wÁÉÍÓÚÑáéíóúñ])", texto):
                extra.append({"inicio": m.start(), "fin": m.end(),
                              "texto": tok, "tipo": "PER"})
        return extra

    def _mapa_personas(self, texto: str, per_textos):
        """Asigna una etiqueta consistente ([PACIENTE_n]/[MEDICO_n]/[PERSONA_n]) a cada
           persona. El subtipo se decide una vez mirando TODAS sus apariciones, y las
           partes del nombre (apellido suelto) heredan la etiqueta del nombre completo."""
        unicos = sorted({t.strip() for t in per_textos if t.strip()},
                        key=lambda s: len(s.split()), reverse=True)  # completos primero

        def subtipo(nombre):
            sub = "PERSONA"
            for m in re.finditer(r"(?<![\wÁÉÍÓÚÑáéíóúñ])" + re.escape(nombre) +
                                 r"(?![\wÁÉÍÓÚÑáéíóúñ])", texto):
                ventana = texto[max(0, m.start() - 25):m.start()]
                if _HON_MEDICO.search(ventana):
                    return "MEDICO"
                if _HON_PACIENTE.search(ventana):
                    sub = "PACIENTE"
            return sub

        etiquetas = {}
        contadores = {}
        for nombre in unicos:
            key = nombre.lower()
            if key in etiquetas:
                continue
            # ¿es parte de un nombre ya etiquetado? -> hereda
            heredada = None
            for otro in unicos:
                if otro.lower() != key and re.search(
                        r"(?<![\wÁÉÍÓÚÑáéíóúñ])" + re.escape(nombre) +
                        r"(?![\wÁÉÍÓÚÑáéíóúñ])", otro):
                    heredada = etiquetas.get(otro.lower())
                    if heredada:
                        break
            if heredada:
                etiquetas[key] = heredada
                continue
            sub = subtipo(nombre)
            contadores[sub] = contadores.get(sub, 0) + 1
            etiquetas[key] = f"[{sub}_{contadores[sub]}]"
        return etiquetas

    def _clasificar_persona(self, texto: str, ini: int) -> str:
        """Decide si un PER es MEDICO o PACIENTE según el honorífico previo."""
        ventana = texto[max(0, ini - 25):ini]
        if _HON_MEDICO.search(ventana):
            return "MEDICO"
        if _HON_PACIENTE.search(ventana):
            return "PACIENTE"
        return "PERSONA"

    # --- proceso principal sobre TEXTO ---
    def anonimizar_texto(self, texto: str, doc_id: str = "doc"):
        hallazgos = reglas_ec.buscar_identificadores(texto)
        ents_ner = self._entidades_ner(texto)
        hallazgos += ents_ner
        # propagar apellidos/nombres sueltos a partir de los PER detectados
        per_textos = [e["texto"] for e in ents_ner if e["tipo"] == "PER"]
        hallazgos += self._propagar_partes_nombre(texto, per_textos)

        # decidir el subtipo de cada nombre UNA sola vez (por texto normalizado),
        # y unificar: si un mismo texto aparece como PER y como LOC/ORG, gana PER.
        prefer_per = {h["texto"].strip().lower() for h in hallazgos if h["tipo"] == "PER"}
        for h in hallazgos:
            if h["tipo"] in ("LOC", "ORG") and h["texto"].strip().lower() in prefer_per:
                h["tipo"] = "PER"

        # resolver solapamientos: prioridad a reglas (más específicas) y a spans largos
        prioridad = {"CEDULA": 5, "RUC": 5, "EMAIL": 5, "TELEFONO": 5, "NUM_HISTORIA": 5,
                     "FECHA": 4, "EDAD_90": 4, "URL": 4, "IP": 4,
                     "PER": 3, "LOC": 2, "ORG": 1}
        hallazgos.sort(key=lambda h: (-prioridad.get(h["tipo"], 0),
                                      -(h["fin"] - h["inicio"])))
        ocupado = [False] * (len(texto) + 1)
        elegidos = []
        for h in hallazgos:
            if any(ocupado[h["inicio"]:h["fin"]]):
                continue
            for i in range(h["inicio"], h["fin"]):
                ocupado[i] = True
            elegidos.append(h)
        elegidos.sort(key=lambda h: h["inicio"])

        # asignación de pseudónimos consistentes
        mapa = {}          # texto_original.lower() -> etiqueta (para LOC/ORG)
        contadores = {}
        # mapa consistente de personas (nombre completo y sus partes comparten etiqueta)
        mapa_personas = self._mapa_personas(
            texto, [h["texto"] for h in elegidos if h["tipo"] == "PER"])
        offset = dt.timedelta(days=self._offset_dias(doc_id)) if self.desplazar_fechas else None
        auditoria = []

        def etiqueta_para(h):
            tipo = h["tipo"]
            if tipo == "PER":
                return mapa_personas.get(h["texto"].strip().lower(), "[PERSONA]")
            elif tipo == "LOC":
                clave = "LUGAR"
            elif tipo == "ORG":
                clave = "ORG"
            elif tipo == "FECHA":
                if self.desplazar_fechas and "fecha" in h:
                    nueva = h["fecha"] + offset
                    return nueva.strftime("%d/%m/%Y")  # fecha desplazada, no etiqueta
                return "[FECHA]"
            else:
                # identificadores estructurados: etiqueta fija por tipo
                return f"[{tipo}]"
            # entidades de persona/lugar/org: numeración consistente
            k = h["texto"].strip().lower()
            if k in mapa:
                return mapa[k]
            contadores[clave] = contadores.get(clave, 0) + 1
            et = f"[{clave}_{contadores[clave]}]"
            mapa[k] = et
            return et

        # reconstruir el texto reemplazando de atrás hacia adelante
        salida = texto
        for h in sorted(elegidos, key=lambda x: x["inicio"], reverse=True):
            rep = etiqueta_para(h)
            salida = salida[:h["inicio"]] + rep + salida[h["fin"]:]
            auditoria.append({"tipo": h["tipo"], "hash": self._hash(h["texto"]),
                              "reemplazo": rep, "len": h["fin"] - h["inicio"]})

        # colapsar etiquetas idénticas consecutivas: "[MEDICO_1] [MEDICO_1]" -> "[MEDICO_1]"
        salida = re.sub(r"(\[[A-ZÑ]+(?:_\d+)?\])(?:\s+\1)+", r"\1", salida)

        resumen = {}
        for a in auditoria:
            resumen[a["tipo"]] = resumen.get(a["tipo"], 0) + 1
        return salida, {"doc_id": doc_id, "total_phi": len(auditoria),
                        "por_tipo": resumen, "detalle": auditoria,
                        "ner": self.usar_ner, "fechas_desplazadas": self.desplazar_fechas}

    # --- proceso sobre PDF (redacción real con PyMuPDF) ---
    def anonimizar_pdf(self, ruta_pdf: Path, ruta_salida: Path):
        import fitz  # PyMuPDF
        doc = fitz.open(ruta_pdf)
        doc_id = ruta_pdf.stem
        total = {}
        n = 0
        for page in doc:
            texto = page.get_text()
            if not texto.strip():
                continue  # página sin texto (escaneada) -> requiere OCR (ver README)
            # misma detección que el camino de texto (reglas + NER + propagación de nombres)
            ents_ner = self._entidades_ner(texto)
            per_textos = [e["texto"] for e in ents_ner if e["tipo"] == "PER"]
            hallazgos = (reglas_ec.buscar_identificadores(texto) + ents_ner +
                         self._propagar_partes_nombre(texto, per_textos))
            for h in hallazgos:
                # las fechas se desplazan en la versión de texto; en PDF se redactan
                for rect in page.search_for(h["texto"]):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    total[h["tipo"]] = total.get(h["tipo"], 0) + 1
                    n += 1
            page.apply_redactions()  # elimina de verdad el contenido subyacente
        doc.save(ruta_salida)
        doc.close()
        return {"doc_id": doc_id, "total_redacciones": n, "por_tipo": total}


def procesar(entrada: Path, salida: Path, anon: Anonimizador):
    salida.mkdir(parents=True, exist_ok=True)
    archivos = [entrada] if entrada.is_file() else sorted(
        [p for p in entrada.iterdir() if p.suffix.lower() in (".txt", ".pdf", ".csv")])
    auditorias = []
    for f in archivos:
        if f.suffix.lower() == ".pdf":
            out = salida / f"{f.stem}_ANON.pdf"
            info = anon.anonimizar_pdf(f, out)
            print(f"[PDF ] {f.name} -> {out.name}  ({info['total_redacciones']} redacciones)")
        else:
            texto = f.read_text(encoding="utf-8", errors="ignore")
            limpio, info = anon.anonimizar_texto(texto, doc_id=f.stem)
            out = salida / f"{f.stem}_ANON{f.suffix}"
            out.write_text(limpio, encoding="utf-8")
            print(f"[TEXT] {f.name} -> {out.name}  ({info['total_phi']} PHI: {info['por_tipo']})")
        auditorias.append(info)
    # log de auditoría global (solo conteos y hashes, sin PHI en claro)
    (salida / "auditoria_anonimizacion.json").write_text(
        json.dumps(auditorias, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[LOG ] auditoria_anonimizacion.json  ({len(auditorias)} documentos)")


def main():
    ap = argparse.ArgumentParser(description="Anonimizador de historias clínicas (CITIMED)")
    ap.add_argument("--entrada", required=True, help="Archivo .txt/.pdf/.csv o carpeta")
    ap.add_argument("--salida", default="salidas", help="Carpeta de salida")
    ap.add_argument("--salt", default=SALT_POR_DEFECTO, help="Sal para hashes y offset de fechas")
    ap.add_argument("--no-desplazar-fechas", action="store_true",
                    help="Reemplaza fechas por [FECHA] en lugar de desplazarlas")
    ap.add_argument("--sin-ner", action="store_true", help="Desactiva spaCy (solo reglas)")
    args = ap.parse_args()

    anon = Anonimizador(salt=args.salt,
                        desplazar_fechas=not args.no_desplazar_fechas,
                        usar_ner=not args.sin_ner)
    if not anon.usar_ner:
        print("[aviso] NER desactivado o modelo spaCy no disponible: "
              "la detección de nombres usará solo reglas/heurística (menor recall).")
    procesar(Path(args.entrada), Path(args.salida), anon)


if __name__ == "__main__":
    main()
