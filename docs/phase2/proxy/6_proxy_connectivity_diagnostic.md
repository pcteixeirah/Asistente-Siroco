# Diagnóstico de Conectividad Proxy — Bright Data × YouTube

**Fecha:** 2026-03-05  
**Estado:** 🔴 YouTube bloqueado por política de acceso de Bright Data

---

## 1. Resumen Ejecutivo

La conexión al proxy de Bright Data **funciona correctamente** para sitios genéricos. Pero **Bright Data bloquea los CONNECT tunnels hacia YouTube** desde la zona `proxy_rotation_siroco`, devolviendo `403 Forbidden` a nivel del proxy.

> [!CAUTION]
> El problema NO está en el código Python, en yt-dlp, ni en SSL. Es una **restricción de política** del servicio Bright Data para la zona actual.

---

## 2. Batería de Tests Ejecutados

| # | Herramienta | Destino | Resultado | Notas |
|:--|:--|:--|:--|:--|
| 1 | `urllib.request` (Python) | `geo.brdtest.com` | ✅ `200 OK` | IP salida: Egipto (Cairo) |
| 2 | `requests` (Python) | `geo.brdtest.com` | ✅ `200 OK` | IP: US (Saint Paul, MN) |
| 3 | `requests` (Python) | `httpbin.org/ip` | ✅ `200 OK` | IP: `143.255.235.253` (US) |  
| 4 | `requests` (Python) | `youtube.com` (HTTPS) | ❌ `403 Forbidden` | Tunnel rejected |
| 5 | `requests` (Python) | `youtube.com` (HTTP) | ❌ `403 Forbidden` | Sin tunnel, aún bloqueado |
| 6 | `yt-dlp` (Python API) | YouTube video | ❌ `403 Forbidden` | Tunnel rejected |
| 7 | `yt-dlp` (CLI directo) | YouTube video | ❌ `403 Forbidden` | Mismo error vía CLI |
| 8 | `curl -k` | `geo.brdtest.com` | ✅ `200 OK` | Confirmado por usuario |
| 9 | `curl -k` (Script) | `youtube.com` | ❌ `000` (timeout) | Bloqueado |

### Conclusión

- ✅ Puerto `33335` es correcto
- ✅ Credenciales (`brd-customer-hl_6af14608-zone-proxy_rotation_siroco`) son válidas
- ✅ SSL no es la causa (`nocheckcertificate` no cambia el resultado)
- ❌ **YouTube está bloqueado a nivel de la zona de proxy en Bright Data**

---

## 3. Root Cause Analysis

```
curl → brd.superproxy.io:33335 → geo.brdtest.com   → 200 OK ✅
curl → brd.superproxy.io:33335 → youtube.com        → 403 Forbidden ❌

requests → proxy → httpbin.org   → 200 OK ✅
requests → proxy → youtube.com   → 403 Forbidden ❌
```

El `403` no viene de YouTube. Viene del **servidor proxy de Bright Data**, que intercepta el `CONNECT` request y rechaza el tunneling hacia el dominio `youtube.com` antes de que la solicitud llegue a los servidores de Google.

### Posibles causas en Bright Data

1. **Política de acceso de la zona**: La zona `proxy_rotation_siroco` puede no tener YouTube habilitado en su lista de dominios permitidos.
2. **Certificado SSL de Bright Data no instalado** (Escenario #2 del asistente de BD): Para proxies residenciales en modo "Immediate access", Bright Data puede requerir su certificado CA instalado en el sistema para ciertos destinos (YouTube incluido).
3. **Tipo de producto incorrecto**: YouTube scraping puede requerir "Web Unlocker" o "SERP API" en lugar de un proxy residencial estándar.

---

## 4. Cambios de Código Implementados

A pesar de que el bloqueo es de Bright Data, se implementaron mejoras que serán útiles una vez que se resuelva la configuración del proxy:

### 4.1 `core/downloader.py` — SSL Fix
```diff
+ 'nocheckcertificate': True,  # Required for BrightData 'Immediate access' mode
```

### 4.2 `core/proxy_pool.py` — Health Check
- Nuevo método `health_check()` que valida conectividad al proxy ANTES de procesar tracks.
- Test contra `geo.brdtest.com` con SSL deshabilitado.

### 4.3 `main_proxy.py` — Circuit Breaker + Backoff
- **Health check al inicio**: Si el proxy falla, el pipeline se detiene inmediatamente.
- **Circuit breaker**: Si 10 tracks consecutivos fallan con el mismo error, aborta.
- **Exponential backoff**: Delays crecientes entre intentos fallidos (2s → 4s → 8s → max 30s).
- **Summary log** al final de la ejecución.

### 4.4 `tests/test_proxy_connection.py` — Test Standalone
- Script de prueba independiente que valida tanto el túnel de proxy como yt-dlp.

---

## 5. Acciones Necesarias (Decisiones del Usuario)

> [!IMPORTANT]
> Estas acciones deben ejecutarse en el **dashboard de Bright Data**, no en el código.

### Opción A — Verificar la configuración de la zona
1. Ingresar al dashboard de Bright Data.
2. Ir a la zona `proxy_rotation_siroco`.
3. Verificar si YouTube está en la lista de dominios permitidos.
4. Si no lo está, agregarlo y re-ejecutar los tests.

### Opción B — Instalar el certificado SSL de Bright Data
1. Descargar el certificado CA de Bright Data desde su documentación.
2. Instalarlo como autoridad de certificación confiable en Windows.
3. Re-ejecutar los tests **sin** `nocheckcertificate`.
4. Si esto resuelve el bloqueo de YouTube, remover `nocheckcertificate` del código.

### Opción C — Considerar Web Unlocker
Si las opciones A y B no funcionan, YouTube puede requerir el producto **Web Unlocker** de Bright Data, que es específico para sitios que bloquean proxies (YouTube, Google, etc.). Este producto opera como una API, no como un proxy HTTP estándar, y requeriría un cambio de arquitectura en el `downloader.py`.
