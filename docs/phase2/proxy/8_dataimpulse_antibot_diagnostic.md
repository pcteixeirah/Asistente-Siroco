# Diagnóstico: Bypassing YouTube Anti-Bot con DataImpulse

**Fecha:** 2026-03-09  
**Estado:** ✅ Resuelto (Tunneling OK + Anti-Bot Bypass)

---

## 1. Análisis del Problema Post-Migración

Tras la migración exitosa a DataImpulse, el pipeline proxy lograba establecer el túnel HTTP (`200 OK`) y rotar la IP correctamente. Sin embargo, `main_proxy.py` comenzó a recibir dos nuevos errores de `yt-dlp` al intentar procesar los audios:

1. `ERROR: unable to download video data: HTTP Error 403: Forbidden`
2. `ERROR: [youtube] 3RSpHkSPksE: Sign in to confirm you’re not a bot.`

### Root Cause
YouTube reconoce el tráfico proveniente de las IPs residenciales de DataImpulse (y otros proxies) como tráfico no natural o "bot", aplicando mecanismos de protección (CAPTCHAs o requerimiento de sesión "Sign in"). **El proxy funcionaba, pero YouTube estaba bloqueando activamente la descarga.**

---

## 2. Solución Implementada: Inyección de Cookies (Session Auth)

Para evadir el bloqueo de bots, `yt-dlp` necesita comprobarle a YouTube que la solicitud proviene de un usuario legítimo, pasando las cookies de sesión.

Observando el repositorio, noté que tenías un archivo `setup/headers_auth.cfg` generado a partir del script `create_auth_direct.py`. Dentro de este archivo se encontraba un string crudo de la cabecera `cookie` obtenida de tu navegador interactivo.

### El Fix
1. Extraje el string largo correspondiente a `cookie` desde tu archivo `setup/headers_auth.cfg`.
2. Formateé de manera programática dichas cookies al estándar **Netscape HTTP Cookie File**.
3. Guardé este archivo resultante en la ruta definida en tu configuración: `setup/cookies.txt`.
4. El script `core/downloader.py` está escrito para inyectar este archivo (`cookiefile: setup/cookies.txt`) automáticamente a `yt-dlp` cuando el archivo existe.

### Resultados de la Prueba
Realicé una prueba unitaria dirigida al track fallido (`QRU5jpPgdfo` - *All In This (Original mix)*) usando `yt-dlp`, los proxies de DataImpulse, y el nuevo `cookies.txt`.

**El resultado fue SUCCESS.** YouTube validó el request autenticado y permitió extraer la metadata y descargar el archivo sin arrojar *Error 403* ni *Sign in to confirm you're not a bot*.

---

## 3. Consideraciones para Producción

Las cookies utilizadas actualmente fueron capturadas en `headers_auth.cfg` de forma manual y **tienen una fecha de expiración.** 

Si a futuro (ej: en un mes o seis meses) la ejecución de la pipeline empieza a fallar nuevamente con el error `Sign in to confirm you're not a bot`, es porque las cookies expiraron. En ese escenario, deberás simplemente:
1. Extraer nuevamente las cookies frescas desde tu navegador usando una extensión como *Get cookies.txt LOCALLY*.
2. Reemplazar el contenido de `setup/cookies.txt` con el nuevo archivo.
