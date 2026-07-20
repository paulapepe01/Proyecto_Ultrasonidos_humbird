#pip3 install numpy scipy soundfile

import os
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, butter, lfilter

# ==============================================================================
# CONFIGURACIÓN MANUAL (MODIFICA ESTO CADA VEZ QUE QUIERAS TRANSFORMAR UN AUDIO)
# ==============================================================================
CARPETA_ENTRADA = "Originales"
CARPETA_SALIDA = "ATAQUES"

# 1. Escribe aquí el nombre exacto de tu archivo (debe estar en COMANDOS_ORIGINALES)
ARCHIVO_ENTRADA = "Bajar_brillo.wav" 

# 2. Escribe aquí la frecuencia a la que quieres subirlo (ej: 18000, 19000 o 20000)
FRECUENCIA_OBJETIVO = 19000 # 18000, 19000 o 20000 Hz

SAMPLE_RATE_SALIDA = 96000 # SR necesario para reproducir ultrasonidos (no tocar)
# ==============================================================================

def filtro_paso_bajo(datos, corte, fs, orden=5):
    """Filtra las frecuencias altas del audio original."""
    nyq = 0.5 * fs
    corte_normal = corte / nyq
    b, a = butter(orden, corte_normal, btype='low', analog=False)
    y = lfilter(b, a, datos)
    return y

def transformar_audio_individual():
    # Crear carpetas si no existen
    os.makedirs(CARPETA_ENTRADA, exist_ok=True)
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    ruta_entrada = os.path.join(CARPETA_ENTRADA, ARCHIVO_ENTRADA)

    # Comprobar que el archivo que has escrito realmente existe
    if not os.path.isfile(ruta_entrada):
        print(f"[ERROR] No se encuentra el archivo '{ARCHIVO_ENTRADA}' en la carpeta '{CARPETA_ENTRADA}'.")
        print("Revisa que el nombre esté bien escrito y que tenga la extensión correcta (.wav, .mp3...).")
        return

    print("==================================================")
    print(f" MODULANDO: {ARCHIVO_ENTRADA} -> {FRECUENCIA_OBJETIVO / 1000} kHz")
    print("==================================================")

    try:
        # 1. Leer archivo original
        datos, fs_original = sf.read(ruta_entrada)
        
        # Convertir a mono si es estéreo
        if len(datos.shape) > 1:
            datos = np.mean(datos, axis=1)

        # 2. Remuestrear al SR objetivo (96 kHz)
        if fs_original != SAMPLE_RATE_SALIDA:
            print(f"[INFO] Remuestreando de {fs_original}Hz a {SAMPLE_RATE_SALIDA}Hz...")
            datos = resample_poly(datos, SAMPLE_RATE_SALIDA, fs_original)

        # 3. Normalizar y limpiar la señal base (mensaje)
        datos = datos / np.max(np.abs(datos))
        datos = filtro_paso_bajo(datos, 8000, SAMPLE_RATE_SALIDA)

        # 4. Crear vector de tiempo
        t = np.arange(len(datos)) / SAMPLE_RATE_SALIDA

        # 5. Generar la modulación
        print("[INFO] Aplicando modulación de amplitud (AM)...")
        portadora = np.cos(2 * np.pi * FRECUENCIA_OBJETIVO * t)
        senal_modulada = (1 + datos) * portadora
        
        # Normalizamos para evitar saturación (clipping) digital
        senal_modulada = senal_modulada / np.max(np.abs(senal_modulada))
        
        # 6. Guardar el archivo final
        nombre_base = os.path.splitext(ARCHIVO_ENTRADA)[0]
        nombre_salida = f"{nombre_base}_{FRECUENCIA_OBJETIVO//1000}kHz.wav"
        ruta_salida = os.path.join(CARPETA_SALIDA, nombre_salida)
        
        sf.write(ruta_salida, senal_modulada, SAMPLE_RATE_SALIDA, subtype='FLOAT')
        print(f"\n[ÉXITO] Archivo generado correctamente: {nombre_salida}")
        print(f"Ya está listo en tu carpeta '{CARPETA_SALIDA}' para usarlo en la interfaz.")

    except Exception as e:
        print(f"[ERROR] Ocurrió un problema procesando el archivo: {e}")

if __name__ == "__main__":
    transformar_audio_individual()