# Proxy Rotation Implementation Plan (Strategy A+C)

**Objetivo**: Integrar soporte de Proxy Rotativo Gestionado y Autenticación con Cookies para mitigar el error `HTTP 403` y permitir scraping de alto volumen.

**Estrategia Seleccionada**:

- **Proveedor de Desarrollo (Testing)**: **BrightData** (Residencial).
- **Proveedor de Producción**: **DataImpulse** (Residencial, bajo costo).
- **Autenticación**: `cookies.txt` + Reclasificación de errores 403.

---

## 1. Critical Fix: Reclasificación de Errores

#### [MODIFY] [core/errors.py]

**Problema**: `HTTP Error 403` es tratado como `permanent`. Esto detiene el reintento aunque rotemos la IP.
**Solución**: Mover `HTTP Error 403` a la lista `_TRANSIENT_PATTERNS`.

```diff
 _PERMANENT_PATTERNS = [
-    r"HTTP Error 403",
     ...
 ]
 _TRANSIENT_PATTERNS = [
+    r"HTTP Error 403",
     ...
 ]
```

---

## 2. Infraestructura: Módulo de Proxy Pool

#### [NEW] [core/proxy_pool.py]

Implementar la clase `ProxyPool` con soporte para modo `gateway`.

```python
class ProxyPool:
    def __init__(self, config):
        self.mode = config.get("mode", "none")
        self.gateway_url = config.get("gateway_url")

    def get_proxy(self):
        if self.mode == "gateway":
            return self.gateway_url
        return None
    
    def rotate(self):
        # En modo gateway, el proveedor rota la IP por cada request.
        # No se requiere acción local, pero loggeamos el evento.
        pass
```

---

## 3. Integración en el Pipeline

#### [MODIFY] [core/downloader.py]

- Recibir `ProxyPool` y `cookies_path` en `__init__`.
- Configurar `yt_dlp` options:
  - `proxy`: `proxy_pool.get_proxy()`
  - `cookiefile`: `cookies_path` (si existe)

#### [MODIFY] [main_proxy.py]

- Cargar configuración de `proxy_rotation`.
- Instanciar `ProxyPool`.
- En caso de error `transient`, llamar a `proxy_pool.rotate()` (simbólico en gateway) y reintentar.

---

## 4. Configuración (BrightData / DataImpulse)

#### [MODIFY] [config.yaml]

Agregar sección `proxy_rotation`.

```yaml
proxy_rotation:
  mode: "gateway" # "gateway" | "none"
  
  # Opción 1: BrightData (Testing)
  # gateway_url: "http://brd-customer-<ID>-zone-<ZONE>:<PASS>@brd.superproxy.io:22225"
  
  # Opción 2: DataImpulse (Producción)
  # gateway_url: "http://<USER>:<PASS>@gw.dataimpulse.com:823"
  
  gateway_url: "" # Placeholder - User must fill this

paths:
  cookies: "setup/cookies.txt"
```

---

## 5. Plan de Validación

1. **Unit Test**: Verificar que `classify_error(Exception("HTTP Error 403"))` retorna `"transient"`.
2. **Connectivity Test**: Script simple que descarga `https://httpbin.org/ip` usando `yt-dlp` con el proxy configurado para verificar que la IP es distinta a la local.
3. **Pilot Run**: Ejecutar `main_proxy.py` con 50 canciones usando BrightData.
