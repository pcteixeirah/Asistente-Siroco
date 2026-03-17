# Diagnóstico del Proyecto SIROCO v3 — Post-Integración GetSongBPM

**Fecha:** 2026-03-13  
**Versión:** 3.0  
**Autor:** Antigravity (Senior BI & ETL Architect)  
**Contexto:** Evaluación posterior a la integración de GetSongBPM API (Fase 2) con análisis de la primera corrida productiva sobre 757 tracks.

---

## 1. Resumen del Proyecto (Estado Actual)

Pipeline ETL automatizado para escanear, analizar y estructurar bibliotecas musicales de YouTube Music.

**Stack actual**: Python 3 · `ytmusicapi` · `requests` · GetSongBPM API · SQLite · `python-dotenv`

**Flujo**:
```
YouTube Music Playlist → Scanner (ytmusicapi) → SQLite → Analyzer (GetSongBPM API) → DB Update
```

---

## 2. Rúbrica de Evaluación Cualitativa

| Categoría | Score | Δ vs v2 | Justificación |
|:--|:--|:--|:--|
| **Extracción** | 🟩 4/5 | ↑ +3 | Scanner funcional, sincronización con YT Music estable. Falta detección de tracks eliminados. |
| **Transformación** | 🟥 2/5 | NUEVO | No existe. Sin clasificación semántica (genre, mood, demographic). Sin enriquecimiento. |
| **Carga** | ⬛ 1/5 | NUEVO | No existe. No se genera ningún output consumible (playlist, CSV, JSON, dashboard). |
| **Match Quality** | 🟧 3/5 | NUEVO | 49.7% tasa de éxito. Scores altos cuando matchea (avg 0.922). Limpieza de títulos insuficiente. |
| **Error Handling** | 🟩 4/5 | ↑ +1 | Clasificador regex actualizado. Circuit breaker activo. Backoff exponencial. |
| **Testing** | 🟨 4/5 | ↑ +3 | Suite con pytest, 8 tests (unit + live API). Falta coverage de scanner y database. |
| **Seguridad** | 🟩 4/5 | ↑ +2 | Credenciales en `.env`. No se loguean secrets. `.gitignore` correcto. |
| **Arquitectura de Datos** | 🟩 4/5 | → | SQLite centralizado. Schema con migraciones dinámicas. `match_score` para QA. |
| **Clean Code** | 🟧 3/5 | → | Buena modularización. `bare except` persisten en scanner. Algunos bloques JSON sin manejo. |
| **Escalabilidad** | 🟥 2/5 | → | Pipeline monohilo síncrono. API tiene rate limit de 3000/h (50 rpm impuesto). |
| **Documentación** | 🟩 5/5 | → | README, backlink, 10 docs técnicos en `docs/phase2/`. |
| **Score Global** | **3.3/5** | ↑ +0.7 | Pipeline parcialmente funcional. Extraction OK. Transform y Load inexistentes. |

---

## 3. Análisis de la Primera Corrida Productiva

### 3.1 Métricas Clave

| Métrica | Valor |
|:--|:--|
| Total tracks en DB | 757 |
| **Status: success** | **376 (49.7%)** |
| **Status: failed** | **381 (50.3%)** |
| Fallos permanentes (not found) | 368 |
| Fallos transitorios | 9 |
| Fallos desconocidos | 4 |
| Match score promedio (exitosos) | 0.922 |
| Match score mínimo aceptado | 0.651 |
| Match score máximo | 1.000 |
| Tracks con danceability | 367 |

### 3.2 Diagnóstico de la Tasa de Fallo (50.3%)

La tasa de éxito de 49.7% es **inaceptable para producción** pero **esperable dada la implementación actual** y **corregible** mediante una mejora sustancial del preprocesamiento de títulos. Análisis de los 368 fallos permanentes:

| Patrón en el Título | Ejemplos | Frecuencia Estimada | Impacto |
|:--|:--|:--|:--|
| **Artista embebido con dash** (`Artist - Song`) | `Andrés Calamaro - Crímenes perfectos`, `Black Sabbath - Iron Man` | ~25% | `_clean_title` no remueve el prefijo del artista |
| **Sufijos no cubiertos por regex** (`Ao Vivo`, `Directo`, `Live On`, `mejorado`) | `Ai Se Eu Te Pego (Ao Vivo)`, `19 Dias y 500 Noches (Directo)` | ~15% | Solo se limpian sufijos en inglés |
| **Metadatos de formato/calidad** (`4K Video`, `HD`, `Remaster 2007`) | `Back In Black (Official 4K Video)`, `Big Poppa (2007 Remaster)` | ~10% | Parcialmente cubierto, muchas variantes no cubiertas |
| **Títulos de nicho/underground** (artistas locales) | `Bombacid`, `Akapelinho`, `NUEVAYoL` | ~30% | No están en la base de datos de GetSongBPM (6M tracks) |
| **Artista como uploader es diferente al artista real** | `Afuera - Caifanes` subido por `PaganoEducado` | ~20% | La query concatena uploader nombre como artista, diluye similitud |

### 3.3 Proyección de Mejora

Con las mejoras propuestas en la Fase 3 (limpieza avanzada de títulos + búsqueda word-by-word), se estima:

| Escenario | Tasa de Éxito Proyectada |
|:--|:--|
| Estado actual | 49.7% |
| Con limpieza avanzada (sufijos + dash + multilingual) | ~65-70% |
| Con búsqueda word-by-word fallback | ~72-78% |
| Irreducible (tracks no disponibles en GetSongBPM) | ~20-25% |

---

## 4. Análisis Crítico del Pipeline ETL

### 4.1 Extract ✅ (Funcional con mejoras menores pendientes)
- Scanner funciona correctamente con `ytmusicapi`.
- No detecta tracks eliminados de la playlist (stale records en DB).
- `INSERT OR IGNORE` no actualiza metadata de tracks que cambian de título.

### 4.2 Transform ❌ (Inexistente — Bloqueo Crítico)

El usuario requiere clasificación semántica: `genre`, `mood`, `demographic`, `tags`. Esto es **la brecha más grande del proyecto**.

**El problema fundamental:** GetSongBPM solo provee `bpm`, `key_of`, `danceability` y `genre` del artista. No provee:
- Mood (dance, sing, chill, energize)
- Demographic (family, couple, solo, social)  
- Genre granular por canción (electrónica, reggaetón, vallenato, etc.)
- Tags semánticos contextuales

**Opciones para implementar Transform:**

| Opción | Viabilidad | Costo | Precisión |
|:--|:--|:--|:--|
| **A. LLM API (Gemini/GPT)** | ✅ Alta | ~$2-5/mes | Alta (80-90%) |
| **B. Modelo local (Gemma 2B)** | ✅ Media-Alta | Gratis (pero CPU/GPU) | Media-Alta (70-85%) |
| **C. Clasificador ML custom** | ⚠️ Baja | Gratis | Baja-Media (requiere dataset etiquetado) |
| **D. Reglas heurísticas (basadas en BPM/key/genre del artista)** | 🟧 Media | Gratis | Baja (50-65%) |

**Recomendación:** Opción A (LLM API) como implementación primaria. Una Gemini Flash (gratis hasta 1500 req/día) puede clasificar 757 tracks en una sola corrida usando prompt engineering. El input sería: nombre de la canción + artista + BPM + key + genres del artista (disponibles en GetSongBPM). El output sería un JSON estructurado con `genre`, `mood`, `demographic`, `tags`.

### 4.3 Load ❌ (Inexistente — Bloqueo Crítico)

No existe ningún mecanismo para convertir la data procesada en un producto consumible. El usuario necesita generar **playlists para YT Music** segmentadas por horario del día (configurado en `config.yaml`).

**Diseño propuesto — Playlist Generator:**
1. Leer config: `schedule: {morning: "06:00-12:00", afternoon: "12:00-18:00", evening: "18:00-00:00"}`
2. Query DB con filtros basados en las tags generadas (mood, energy, etc.)
3. Construir playlist de ~2 horas (basada en duración estimada por track ~3.5 min = ~34 tracks)
4. Publicar en YT Music usando `ytmusicapi.create_playlist()` o actualizar playlist existente

---

## 5. Análisis de Clean Code

### Problemas Detectados

| Archivo | Problema | Severidad |
|:--|:--|:--|
| `scanner.py:75` | `bare except` silencia errores de playlist | Media |
| `database.py` | Nueva conexión por cada operación (`_get_connection`) | Media |
| `database.py:121` | `json.loads` con try/except vacío para artist | Baja |
| `main.py:87-90` | Parsing de artist con try/except implícito | Baja |
| `analyzer.py` | Rate limiter implementado con `time.sleep` — bloqueante | Baja |
| `config.py:33` | `max_tracks_to_process: 500` hardcoded pero config dice `0` | Baja-Media |

### Deuda Técnica Acumulada
- `downloader.py` y `proxy_pool.py` eliminados pero potencialmente referenciados en imports residuales
- `core/__pycache__` puede contener bytecode de módulos eliminados
- `requirements.txt` limpiado pero venv aún tiene paquetes instalados de fases anteriores

---

## 6. Escalabilidad

| Aspecto | Estado | Recomendación |
|:--|:--|:--|
| Pipeline monohilo | Rate limit del API (50 rpm) hace que paralelismo no tenga sentido | Aceptable por ahora |
| SQLite | Suficiente para <10K tracks, single-user | Aceptable |
| API Rate Limit | 3000 req/h = 50/min. 757 tracks = ~15 min | Aceptable |
| Batch processing breakpoints | Circuit breaker y backoff implementados | ✅ |
| Idempotencia | `INSERT OR IGNORE` + status checks | ✅ |

---

## 7. Documentos Relacionados

- [Diagnóstico v2](7_project_diagnostic_v2.md) — Estado pre-GetSongBPM
- [Arquitectura Definitiva](9_definitive_scraping_architecture.md) — Comparación de enfoques
- [Integración GetSongBPM](10_getsongbpm_integration.md) — Documentación técnica de Fase 2
