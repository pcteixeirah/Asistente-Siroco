import librosa
import numpy as np
import pandas as pd
import os
from tqdm import tqdm

# --- Configuración ---
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
PLAYLIST_DIR = os.path.dirname(__file__)
OUTPUT_CSV = os.path.join(PLAYLIST_DIR, "audio_analysis.csv")
SAMPLE_RATE = 22050
DURATION = 60 # Analizar solo los primeros 60 segundos para velocidad

# --- Lógica de Detección de Key (Tonalidad) ---
# Basado en Krumhansl-Schmuckler Key-Finding Algorithm (simplificado)
# Perfiles de tonalidad: Intensidad esperada de cada nota (C, C#, D...) para una tonalidad dada.
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# Nombres de notas para mapear el resultado
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def estimate_key(y, sr):
    """
    Estima la tonalidad (Key) comparando el cromagrama con perfiles de acordes.
    Retorna: string (ej: "C maj", "A min")
    """
    # 1. Extraer Chromagram (Energía por cada nota musical)
    chroma = librosa.feature.chroma_cens(y=y, sr=sr)
    
    # 2. Promediar el chromagrama sobre el tiempo para obtener el "vector de tonalidad" de la canción
    # Forma: (12,) donde cada valor es la intensidad promedio de C, C#, etc.
    chroma_mean = np.mean(chroma, axis=1)
    
    # 3. Correlación con perfiles
    # Rotamos el perfil Major/Minor 12 veces (para probar C maj, C# maj, etc.) y calculamos correlación
    maj_corrs = []
    min_corrs = []
    
    for i in range(12):
        # Rotar perfil matchar con la tónica 'i'
        profile_maj = np.roll(MAJOR_PROFILE, i)
        profile_min = np.roll(MINOR_PROFILE, i)
        
        # Correlación de Pearson
        maj_corrs.append(np.corrcoef(chroma_mean, profile_maj)[0, 1])
        min_corrs.append(np.corrcoef(chroma_mean, profile_min)[0, 1])
        
    # 4. Encontrar el mejor match
    best_maj_idx = np.argmax(maj_corrs)
    best_min_idx = np.argmax(min_corrs)
    
    max_maj_val = maj_corrs[best_maj_idx]
    max_min_val = min_corrs[best_min_idx]
    
    if max_maj_val > max_min_val:
        return f"{NOTE_NAMES[best_maj_idx]} maj"
    else:
        return f"{NOTE_NAMES[best_min_idx]} min"

def analyze_track(filepath):
    """
    Carga y analiza un archivo de audio. Retorna dict con features.
    """
    try:
        # Cargar audio (optimizado con duration y mono=True)
        y, sr = librosa.load(filepath, sr=SAMPLE_RATE, duration=DURATION, mono=True)
        
        # BPM
        # onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        
        # Key
        key = estimate_key(y, sr)
        
        # Duración Total (estimada del archivo completo, no del crop)
        total_duration = librosa.get_duration(path=filepath)
        
        # Energía (RMS)
        rms = librosa.feature.rms(y=y)
        rms_mean = np.mean(rms)
        # Escalar a 1-10: RMS típico es ~0.01 a 0.1+. x100 nos da 1-10+.
        energy_score = int(min(max(rms_mean * 100, 1), 10))

        return {
            "filename": os.path.basename(filepath),
            "bpm_estimated": int(round(tempo)) if isinstance(tempo, float) else int(round(tempo[0])),
            "key_estimated": key,
            "energy_rms": energy_score,
            "duration_sec": round(total_duration, 2),
            "status": "success"
        }
    except Exception as e:
        return {
            "filename": os.path.basename(filepath),
            "bpm_estimated": None,
            "key_estimated": None,
            "energy_rms": None,
            "duration_sec": None,
            "status": f"error: {str(e)}"
        }

def main():
    print(f"--- Iniciando Análisis de Audio en: {ASSETS_DIR} ---")
    
    if not os.path.exists(ASSETS_DIR):
        print("Carpeta assets no encontrada.")
        return

    # Filtrar archivos de audio
    files = [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
    
    if not files:
        print("No se encontraron archivos de audio.")
        return

    results = []
    
    # Barra de progreso
    for file in tqdm(files, desc="Analizando pistas"):
        full_path = os.path.join(ASSETS_DIR, file)
        data = analyze_track(full_path)
        results.append(data)
        
    # Guardar CSV
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"\n[OK] Análisis completado. Reporte guardado en: {OUTPUT_CSV}")
    print(df[['filename', 'bpm_estimated', 'key_estimated', 'status']])

if __name__ == "__main__":
    main()
