# Fase 2: Integración de GetSongBPM API — Documentación Técnica

**Fecha:** 2026-03-13  
**Estado:** ✅ Implementado y Testeado

---

## 1. Contexto

Tras el fracaso de las rutas anteriores (yt-dlp/proxies bloqueado por Anti-Bot de YouTube, Spotify Web API deprecada y restringida a cuentas Premium), se implementó una integración con la **API REST de GetSongBPM** (`getsongbpm.com`) para obtener características musicales de forma oficial, gratuita y confiable.

## 2. Arquitectura Implementada

```
PlaylistScanner (scanner.py) → DB (database.py)
       ↓
AudioAnalyzer (analyzer.py) ← GetSongBPM REST API
       ↓
DB.update_analysis() → status: success | partial_fail
```

### Flujo del Analyzer:
1. Limpia el título del track (remueve sufijos como `(Official Video)`, `[Lyrics]`)
2. Busca en GetSongBPM vía endpoint `/search/` (primero título+artista, luego fallback solo título)
3. Puntúa todos los resultados por similitud textual (`SequenceMatcher`)
4. Rechaza matches con puntuación menor al umbral configurable (default: 0.65)
5. Extrae BPM, Key y Danceability directamente del JSON de búsqueda

## 3. Datos Disponibles

| Campo | Fuente | Formato |
|:--|:--|:--|
| `bpm` | GetSongBPM `tempo` | Entero (ej: 89) |
| `key` | GetSongBPM `key_of` | Notación estándar Unicode (ej: `C♯`, `D`) |
| `danceability` | GetSongBPM `danceability` | Float 0.0-1.0 (normalizado desde 0-100) |
| `match_score` | Calculado internamente | Float 0.0-1.0 |
| `energy_rms`, `valence`, `duration` | No disponible | `NULL` |

## 4. Configuración

**`config.yaml`**: Bloque `getsongbpm` con `base_url`, `match_threshold`, `rate_limit_rpm`.  
**`.env`**: Variable `GETSONGBPM_API_KEY`.

### Límites de la API:
- 3.000 requests/hora (rate limit conservador implementado en código: 50 rpm)
- Requiere backlink a getsongbpm.com en productos públicos
- Ante exceder el rate limit, responde `HTTP 429` y bloquea la key por 1 hora

## 5. Testing

Suite de test en `tests/test_getsongbpm_analyzer.py`:
- **TestInitialization**: Verifica API key y configuración
- **TestKnownTrackSearch**: Busca "Despacito" y valida BPM (89), Key (D), Danceability
- **TestTitleCleaning**: 4 casos unitarios de limpieza de sufijos YouTube
- **TestMatchThreshold**: Verifica rechazo de queries sin sentido

**Resultado:** 8/8 tests pasados ✅

## 6. Archivos Modificados

| Archivo | Cambio |
|:--|:--|
| `core/analyzer.py` | Reescrito para GetSongBPM REST API |
| `core/config.py` | Defaults actualizados (getsongbpm) |
| `core/errors.py` | Patrones de clasificación actualizados |
| `core/database.py` | Columna `match_score` añadida, `update_analysis` flexible |
| `main.py` | Pipeline sin proxies ni descarga, solo API |
| `config.yaml` | API key reference, thresholds, rate limits |
| `.env` / `.env.example` | Credenciales GetSongBPM |
| `requirements.txt` | Removido `spotipy`, conservado `requests` |
| `tests/test_getsongbpm_analyzer.py` | Suite nueva con 8 tests |
