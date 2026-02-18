# Proxy de Análisis con Low-Fi Downsampling

Este documento detalla la transición de descargas completas a un sistema de ingesta ligera basado en metadatos y análisis de baja fidelidad, optimizado para velocidad y eficiencia.

## Fase 1: Capa de Persistencia y Deduplicación (El Cerebro)

El objetivo es evitar procesar dos veces el mismo track. Se implementará una base de datos ligera (SQLite) que actuará como el "Registry" del proyecto.

### Esquema de Base de Datos

Crear una tabla `tracks` en `data/siroco_registry.db` con los siguientes campos:

| Campo | Tipo | Notas |
| :--- | :--- | :--- |
| `yt_id` | TEXT | Primary Key (Video ID de YouTube) |
| `title` | TEXT | Título normalizado |
| `artist` | TEXT | Lista de artistas (JSON string) |
| `album` | TEXT | Título del álbum |
| `genre` | TEXT | Género principal (si disponible) |
| `bpm` | INTEGER | BPM Detectado |
| `key` | TEXT | Tonalidad estimada (e.j. "C min") |
| `energy_rms` | INTEGER | Score de energía (1-10) |
| `duration` | REAL | Duración en segundos |
| `last_analyzed` | TIMESTAMP | Fecha de último análisis |
| `status` | TEXT | 'success', 'failed', 'pending' |
| `file_path_metadata` | TEXT | JSON con huella digital y rutas relativas |

### Módulo de Verificación

Implementar `check_registry(yt_id)` en `core/database.py`:

- Consulta rápida por `yt_id`.
- Retorna `False` si el track no existe o si `status == 'failed'` (y ha pasado X tiempo para reintento).
- Retorna los datos cacheados si ya existe y el análisis es válido.

### Extracción de Metadatos Extendidos

Modificar `extract_playlist.py` para aprovechar al máximo `ytmusicapi`:

- **Género**: Intentar extraerlo de la metadata de álbum o playlist si está disponible.
- **Álbum**: Persistir el nombre del álbum para agrupaciones.
- **Guardado Inmediato**: Insertar en SQLite tan pronto se obtienen los metadatos básicos, marcando `status='pending'` para el análisis de audio.

## Fase 2: Ingesta Low-Fi y Análisis "On-the-Fly"

Aquí es donde resolvemos el cuello de botella técnico de descargar archivos de alta calidad innecesariamente.

### Pipeline de Descarga Minimalista

Configurar `yt-dlp` en `core/downloader.py` para forzar la descarga del stream de menor bitrate aceptable para análisis musical:

- **Formato**: `bestaudio[abr<=64]/worst` (Buscamos ~48kbps a 64kbps).
- **Contenedor**: `.m4a` o `.opus` (ligeros y rápidos de decodificar).
- **Post-procesamiento**: Ninguno (evitar conversión a MP3 para ganar velocidad).

### Normalización de Señal para Librosa

En `core/analyzer.py` (basado en `playlist/analyze_sample.py`):

1. **Carga Optimizada**:

    ```python
    y, sr = librosa.load(path, sr=22050, mono=True)
    ```

    - `sr=22050`: Suficiente para detectar BPM, Key y Energía RMS.
    - `mono=True`: Reduce la memoria a la mitad.

2. **Filtrado Pasa-Banda**:
    - Aplicar un filtro (e.g., Butterworth) para mantener frecuencias entre ~60Hz y ~8000Hz.
    - **Objetivo**: Eliminar ruido de baja frecuencia y artefactos de compresión de alta frecuencia del audio low-fi.

### Cálculo de Features

Ejecutar el análisis sobre la señal limpia:

- **BPM**: `librosa.beat.beat_track` (ya implementado).
- **Energía**: `librosa.feature.rms`, normalizado a escala 1-10.
- **Tonalidad**: Algoritmo Krumhansl-Schmuckler (ya implementado).

### Limpieza Automática

- Una vez extraídos `bpm`, `key` y `energy`, actualizar la DB con los valores.
- **Eliminar inmediatamente** el archivo de audio de `data/temp_cache/`.
- El sistema no debe retener archivos de audio, solo conocimiento.

## Fase 3: Orquestación y Escalabilidad

### Procesamiento por Lotes (Batching)

En `main_proxy.py`:

- Implementar un bucle que procese la playlist en **bloques de 5 tracks**.
- Entre cada bloque, realizar una **pausa aleatoria de 2-5 segundos**.
- Esto minimiza el riesgo de bloqueo por parte de YouTube (HTTP 429).

### Manejo de Errores y Retries

- Si `yt-dlp` falla (e.g., Geo-blocked, Copyright):
  - Marcar en DB `status: failed`.
  - Registrar el error en `logs/errors.log`.
  - **No reintentar** inmediatamente. El sistema debe saltar al siguiente track.

### API de Consulta Interna

Interfaz simple para el Agente DJ (consumidor):

```python
def get_track_analysis(yt_id):
    """
    1. Consulta DB local.
    2. Si no existe, dispara el pipeline de Ingesta Low-Fi (descarga -> analiza -> borra).
    3. Retorna JSON estandarizado para Virtual DJ.
    """
```
