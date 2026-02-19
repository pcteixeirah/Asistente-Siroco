# Análisis Crítico del Proyecto SIROCO

## 1. Resumen Ejecutivo

**SIROCO** es un pipeline de análisis musical automático que: extrae playlists de YouTube Music, descarga audio en baja fidelidad, analiza features musicales (BPM, Key, Energía) vía Librosa, y almacena resultados en SQLite.

### Resultados de la Base de Datos (`siroco_registry.db`)

| Métrica | Valor |
|:--|:--|
| Total de tracks | **733** |
| Status `success` | **640 (87.3%)** |
| Status `failed` | **93 (12.7%)** |
| Status `pending` | **0** |

> [!TIP]
> Un 87.3% de éxito es un punto de partida razonable para un pipeline que depende de descargas de YouTube. El 12.7% de fallos se atribuye probable y principalmente a videos geo-bloqueados, con copyright restringido, o eliminados.

---

## 2. Auditoría Arquitectónica

### 2.1 Estructura Actual

```text
Asistente_Siroco/
├── core/
│   ├── analyzer.py      # Análisis con Librosa (BPM, Key, Energy)
│   ├── database.py      # CRUD SQLite (SirocoRegistry)
│   ├── downloader.py    # Wrapper yt-dlp (LowFiDownloader)
│   └── scanner.py       # Sync YouTube playlist ↔ JSON local
├── data/
│   ├── siroco_registry.db
│   └── temp_cache/
├── playlist/            # ← A eliminar según tu plan
│   ├── siroco_playlist.json  # ← Mover a data/
│   ├── analyze_sample.py     # ← Código muerto / legacy
│   └── audio_analysis.csv    # ← Residuo de pruebas
├── tests/               # 6 scripts sueltos, no son tests reales
├── main_proxy.py        # Orquestador
└── inspect_db.py        # Utilidad ad-hoc
```

### 2.2 Veredicto Arquitectónico: 🟡 Funcional pero Frágil

#### ✅ Lo que está bien

- **Separación de responsabilidades**: Cada módulo en `core/` tiene un rol claro (Scanner, Downloader, Analyzer, Database).
- **Patrón proxy con cache**: Descargar → analizar → borrar → persistir. Eficiente en disco.
- **Deduplicación por `yt_id`**: Evita reprocesamiento innecesario.
- **Low-fi downloading**: Descargar a ≤64kbps es inteligente para solo extraer features.
- **Batch con delay aleatorio**: Minimiza riesgo de rate-limiting de YouTube.

#### 🔴 Problemas Críticos

**1. `check_registry()` retorna `False` para tracks fallidos — pero `main_proxy` espera `dict` o `False`**

```python
# database.py línea 58-59
if data['status'] == 'failed':
    return False  # ← Esto impide re-intentar tracks fallidos
```

En `main_proxy.py` líneas 76-81, el código verifica:

```python
cached_data = db.check_registry(yt_id)
if cached_data:
    if cached_data['status'] == 'success':
        continue
    elif cached_data['status'] == 'failed':
        # Re-try logic
```

Pero `check_registry` **NUNCA retorna un dict con `status='failed'`** — retorna `False`. Esto significa que **los tracks fallidos siempre se re-procesan como si fueran nuevos**, pero primero se les hace `add_track_metadata()` con `INSERT OR REPLACE`, lo cual **borra sus datos de análisis previos** (bpm, key, etc.) porque el INSERT OR REPLACE solo inserta los campos de metadata, no los de análisis.

> [!CAUTION]
> Bug activo: `INSERT OR REPLACE` en `add_track_metadata()` (línea 87) destruye cualquier dato de análisis previo al reinsertar un track. Cada ejecución de `main_proxy` potencialmente resetea tracks que ya tenían análisis parcial.

**2. Sin gestión de configuración centralizada**

Rutas hardcodeadas dispersas en múltiples archivos:

- `"data/siroco_registry.db"` en `database.py`
- `"data/temp_cache"` en `downloader.py`
- `"playlist/siroco_playlist.json"` via path relativo en `scanner.py`
- Playlist ID hardcodeado como constante global

**3. Sin retry inteligente para downloads fallidos**

No hay distinción entre tipos de fallo (geo-block vs. error transitorio vs. video eliminado). Todos se marcan igual como `'failed'`, sin timestamp de expiración ni contador de reintentos.

**4. Zero tests reales**

La carpeta `tests/` contiene 6 scripts utilitarios que **no son pruebas automatizadas**. Son scripts de verificación manual (check_metadata, debug_account_info, etc.). No hay `pytest`, `unittest`, ni ningún framework de testing.

**5. JSON como source of truth paralela a la DB**

El `siroco_playlist.json` (364KB, ~733 tracks) y la DB contienen datos parcialmente superpuestos. El JSON tiene campos `analysis.bpm`, `analysis.key` que **nunca se actualizan** después del análisis. Hay un campo `energy` tanto en el JSON raíz como en `analysis.energy`, creando ambigüedad.

---

## 3. Análisis de la Señal Musical

### 3.1 Detección de BPM

| Métrica | Valor |
|:--|:--|
| Rango detectado | 0 - 199 BPM |
| Promedio | 120.5 BPM |
| Outliers (BPM < 60) | 2 tracks |
| Outliers (BPM > 200) | 0 tracks |

**Distribución por bandas:**

| Banda BPM | Tracks |
|:--|:--|
| 0-80 | 26 |
| 80-100 | 164 |
| 100-120 | 151 |
| 120-140 | 134 |
| 140-160 | 74 |
| 160-200 | 91 |

> [!WARNING]
> **2 tracks con BPM = 0** — Esto indica que `librosa.beat.beat_track` falló silenciosamente pero el track se marcó como `success`. No hay validación post-análisis.

**Crítica técnica del enfoque BPM:**

- `librosa.beat.beat_track` es un estimador de tempo basado en onset strength. Opera bien en música con kick/snare prominente, pero **es notoriamente impreciso con**:
  - Música acústica/folk/bolero (abundante en tu playlist colombiana)
  - Tracks con cambios de tempo
  - Audio de baja calidad (que es exactamente tu caso con ≤64kbps)
- **No se implementó el filtrado pasa-banda** que tu propio documento `musical_analysis_proxy.md` proponía en la Fase 2. Esto era clave para limpiar artefactos de compresión del audio low-fi.
- El BPM no se valida contra rangos musicalmente plausibles (e.g., 40-220 BPM). Un BPM de 0 jamás debería pasar.

### 3.2 Detección de Tonalidad (Key)

Se usa el **algoritmo Krumhansl-Schmuckler** con perfiles de correlación. Las claves detectadas se distribuyen razonablemente:

- G min, C min, D# maj aparecen como las más frecuentes.
- Todas las 24 tonalidades (12 mayores + 12 menores) están representadas.

**Crítica técnica:**

- Se usa `chroma_cens` (chromagram normalizado), que es una buena elección para robustez.
- El enfoque es **la media del chromagram sobre todo el track** — esto pierde modulaciones y secciones contrastantes. Un track que modula de Am a C maj dará un resultado indeterminado.
- No hay **confidence score**: la correlación se calcula pero no se reporta. Sería muy útil saber si la key se detectó con 95% o 55% de confianza.
- La key es una de las features más difíciles de estimar en audio comprimido a 48-64kbps. Los armónicos superiores son los primeros en degradarse por la compresión.

### 3.3 Energía (RMS)

| Nivel | Tracks |
|:--|:--|
| E1 | 5 |
| E2 | 5 |
| E3 | 46 |
| E4 | 44 |
| E5 | 55 |
| E6 | 42 |
| E7 | 34 |
| E8 | 8 |
| E9 | 42 |
| E10 | 359 |

> [!CAUTION]
> **359 de 640 tracks (56%) tienen energía = 10.** Esto indica un problema severo de calibración. La fórmula `int(min(max(rms_mean * 100, 1), 10))` escala linealmente RMS × 100 y la satura en 10. Esto produce una distribución completamente sesgada donde la mayoría de los tracks llegan al tope.

**Problemas con la métrica de energía:**

- RMS depende enormemente del **loudness/gain del audio descargado**, que varía por video.
- No hay **normalización de loudness** (e.g., EBU R128 / ReplayGain) antes de calcular RMS.
- La fórmula de escalado (`rms * 100, clamp 1-10`) es ad-hoc y no está validada.
- El concepto de "energía" en DJ mezcla RMS con danceability, spectral centroid, y percusividad — aquí solo se mide volumen promedio.

### 3.4 Duración

| Métrica | Valor |
|:--|:--|
| Mínima | ~85s |
| Máxima | ~1412s (~23 min) |
| Promedio | ~276s (~4.6 min) |

La duración es la feature más confiable — proviene directamente del decodificador. Un track de 23 minutos podría ser un live set o un video-compilación, vale la pena filtrarlos.

---

## 4. Cobertura de Metadata

| Campo | Cobertura | Nota |
|:--|:--|:--|
| `artist` | Alta (~90%+) | Proviene del JSON, formato JSON string |
| `album` | Media | Muchos tracks de YouTube no tienen álbum |
| `playlist` | Alta | Siempre se asigna "AZC" |
| `popularity` | Baja | Solo los tracks que fueron curados manualmente en el JSON |
| `demographic` | Baja | Idem — datos manuales |
| `tags` | **0%** | Ningún track tiene tags |
| `genre` | **0%** | Ningún track tiene género |

> [!IMPORTANT]
> Los campos `popularity`, `demographic` y `energy` en el JSON son datos curados **manualmente** — no provienen de ninguna API. El pipeline no tiene forma de poblar estos campos automáticamente.

---

## 5. Resumen de Problemas por Severidad

### 🔴 Críticos (afectan la fiabilidad de datos)

1. **Bug `INSERT OR REPLACE`** destruye datos de análisis al re-ejecutar el pipeline.
2. **Energía RMS saturada** — 56% de tracks en el tope (E10). La métrica es inútil para clasificación.
3. **BPM = 0** aceptado como success — falta validación post-análisis.
4. **Falta filtrado pasa-banda** documentado en tu propio plan pero no implementado.

### 🟡 Importantes (afectan escalabilidad y mantenibilidad)

5. JSON y DB como fuentes paralelas con esquemas divergentes (campo `analysis` en JSON nunca se actualiza).
2. Zero tests automatizados.
3. Sin configuración centralizada — rutas y constantes hardcodeadas.
4. Sin retry inteligente ni clasificación de errores de descarga.
5. Sin normalización de loudness pre-análisis.

### 🟢 Mejoras Recomendadas

10. Agregar confidence score a la detección de key.
2. Filtrar tracks por duración (excluir >15 min o <30s).
3. Mover `siroco_playlist.json` a `data/` y eliminar carpeta `playlist/`.
4. Agregar campo `error_type` y `retry_count` a la tabla de tracks.
5. Considerar `essentia` o `madmom` como complemento/alternativa a Librosa para BPM en audio comprimido.
