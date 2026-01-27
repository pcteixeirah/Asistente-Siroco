# Proyecto Asistente YTMusic

## Estructura del Directorio

- **setup/**: Contiene scripts de autenticación y configuración.
  - `headers_auth.cfg`: Archivo de autenticación (formato JSON/CLAVE-VALOR).
  - `create_auth_direct.py`: Script para generar `headers_auth.cfg` a partir de cabeceras en bruto.
- **tests/**: Contiene scripts de prueba y depuración.
  - `get_account_info.py`: Recupera información de la cuenta para verificar la autenticación.
  - `debug_account_info.py`: Inspecciona los métodos del objeto `YTMusic`.
  - `get_playlist.py`: Obtiene y muestra pistas aleatorias de una playlist pública.
- **venv/**: Entorno virtual de Python.

## Configuración de Autenticación

Si necesitas actualizar tu autenticación (por ejemplo, si las cookies caducan):

1.  **Obtener nuevas cabeceras**:
    - Ve a https://music.youtube.com en tu navegador (con sesión iniciada).
    - Abre las Herramientas de Desarrollo (F12) -> pestaña Red (Network).
    - Recarga la página y busca una solicitud a `browse` (o similar).
    - Copia los **Request Headers** (Cabeceras de Solicitud).

2.  **Actualizar `create_auth_direct.py`**:
    - Abre `setup/create_auth_direct.py`.
    - Pega tus nuevas cabeceras en bruto en la variable `raw_headers`.
    - Guarda el archivo.

3.  **Ejecutar el script de actualización**:
    ```powershell
    .\venv\Scripts\python setup/create_auth_direct.py
    ```
    Esto regenerará `setup/headers_auth.cfg`.

4.  **Verificar**:
    ```powershell
    .\venv\Scripts\python tests/get_account_info.py
    ```
