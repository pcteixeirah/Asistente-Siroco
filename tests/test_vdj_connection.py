import subprocess
import os
import time

# --- Configuración ---
# Ruta al ejecutable de Virtual DJ (Verificado en el sistema)
VDJ_PATH = r"C:\Program Files\VirtualDJ\virtualdj.exe"

# Ruta relativa al archivo de audio (Desde la raíz del proyecto)
# Nota: Usamos os.path.abspath para asegurar que VDJ reciba la ruta completa y correcta.
AUDIO_FILE_REL = r"assets\Daft Punk - One More Time.mp3"

def launch_vdj_with_track():
    """
    Localiza VDJ, verifica el archivo y lanza la aplicación cargando la pista.
    """
    print("--- Iniciando Integración con Virtual DJ ---")

    # 1. Validación de Archivos
    if not os.path.exists(VDJ_PATH):
        print(f"[ERROR] No se encontró Virtual DJ en: {VDJ_PATH}")
        return

    base_dir = os.path.dirname(os.path.dirname(__file__)) # Subir un nivel desde 'tests/'
    audio_full_path = os.path.join(base_dir, AUDIO_FILE_REL)

    if not os.path.exists(audio_full_path):
        print(f"[ERROR] No se encontró el archivo de audio en: {audio_full_path}")
        # Listar contenido de assets para debugging si falla
        assets_dir = os.path.join(base_dir, "assets")
        if os.path.exists(assets_dir):
            print(f"Contenido de {assets_dir}: {os.listdir(assets_dir)}")
        return

    print(f"[OK] Archivo de audio encontrado: {audio_full_path}")

    # 2. Construcción del Comando
    # Virtual DJ acepta la ruta de un archivo como argumento para cargarlo en el deck activo (o Deck 1 por defecto).
    # Para "Play" automático, VDJ generalmente requiere configuración interna (Settings -> AutoPlayOnLoad)
    # o comandos más avanzados vía VDJScript.
    # Intentaremos pasar el archivo directamente primero.
    
    # NOTA TÉCNICA: subprocess.Popen es no-bloqueante, lo que permite que el script de Python termine
    # mientras VDJ sigue corriendo.
    
    command = [VDJ_PATH, audio_full_path]
    
    print(f"Lanzando aplicación: {VDJ_PATH}")
    print(f"Comando enviado: {command}")
    
    try:
        # Lanzamos el proceso
        process = subprocess.Popen(command)
        print(f"[EXITO] Virtual DJ lanzado con PID: {process.pid}")
        print("La pista debería cargarse automáticamente en el Deck A/1.")
        
    except Exception as e:
        print(f"[FATAL] Fallo al ejecutar subprocess: {e}")

if __name__ == "__main__":
    launch_vdj_with_track()
