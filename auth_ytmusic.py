"""
YouTube Music Authentication Helper

Run this script to authenticate ytmusicapi.
It will guide you through the process of extracting headers from your browser
and saving them to setup/headers_auth.cfg
"""

import os
from ytmusicapi import setup

AUTH_FILE = "setup/headers_auth.cfg"

def main():
    print("="*60)
    print(" 🎶 SIROCO - YouTube Music Authentication")
    print("="*60)
    print("Instrucciones Actualizadas:")
    print("1. Abre YouTube Music (music.youtube.com).")
    print("2. Toca F12 (Herramientas de Desarrollador) -> pestaña Network (Red).")
    print("3. Haz clic en la pestaña 'Fetch/XHR' justo debajo de Network.")
    print("4. Reproduce una canción o ve a tu Biblioteca.")
    print("5. Busca la petición 'browse?prettyPrint=false' o 'next'.")
    print("6. Haz UNO DE ESTOS DOS METODOS:")
    print("   A) Selecciona la petición, ve a la pestaña 'Headers' a la derecha,")
    print("      busca 'Request Headers', y copia todo el bloque de texto debajo.")
    print("   B) Clic derecho en la petición -> Copy -> Copy Request Headers.")
    print("="*60)
    print(" Pega tu texto copiado aquí abajo.")
    print(" IMPORTANTE: Cuando termines de pegar, simplemente escribe EOF y presiona ENTER.")
    print("="*60)
    
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    
    # Leer entrada multilinea hasta que el usuario escriba EOF
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == 'EOF':
                break
            lines.append(line)
        except EOFError:
            break
            
    raw_headers = '\\n'.join(lines)
    
    if len(raw_headers.strip()) < 10:
        print("\n[ERROR] No detecté ningún texto. Intenta de nuevo.")
        return

    # Usar el método interno setup() con la entrada como string
    try:
        setup(filepath=AUTH_FILE, headers_raw=raw_headers)
        if os.path.exists(AUTH_FILE):
             print(f"\n✅ ¡Autenticación exitosa! Cabeceras guardadas en {AUTH_FILE}")
        else:
             print("\n❌ Fallo en la autenticación.")
    except Exception as e:
        print(f"\n❌ Error guardando las credenciales: {e}")
        print("Asegúrate de copiar el bloque completo de 'Request Headers'.")


if __name__ == "__main__":
    main()
