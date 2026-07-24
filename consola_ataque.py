# ==============================================================================
# PROYECTO: CONSOLA DE ATAQUE ULTRASÓNICO (MODULADOR AM + CONTROL HUMBIRD)
# ==============================================================================

import os
# Suprimir la advertencia de Tk en macOS
os.environ.setdefault('TK_SILENCE_DEPRECATION', '1')

import subprocess
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import tkinter as tk
from tkinter import messagebox
from scipy.signal import resample_poly, butter, lfilter

# --- CONFIGURACIÓN MANUAL DEL ENTORNO ---
SISTEMAS_OP = ["MacOS", "Windows", "Linux"]
SISTEMA_ACTUAL = SISTEMAS_OP[0]  # Cambiar según sistema operativo

NOMBRE_ALTAVOZ = "Humbird Speaker" 
VOLUMEN_SEGURO = 80
SAMPLE_RATE_SALIDA = 96000

# Rutas relativas al script
DIRECTORIO_BASE = os.path.dirname(__file__)
CARPETA_ENTRADA = os.path.join(DIRECTORIO_BASE, "PruebasP")
CARPETA_SALIDA = os.path.join(DIRECTORIO_BASE, "ATAQUES")

# Crear carpetas si no existen
os.makedirs(CARPETA_ENTRADA, exist_ok=True)
os.makedirs(CARPETA_SALIDA, exist_ok=True)


# ==============================================================================
# BLOQUE 1: PROCESAMIENTO DIGITAL DE SEÑALES (DSP)
# ==============================================================================

def filtro_paso_bajo(datos, corte, fs, orden=5):
    """Filtra las frecuencias altas del audio original."""
    nyq = 0.5 * fs
    corte_normal = corte / nyq
    b, a = butter(orden, corte_normal, btype='low', analog=False)
    y = lfilter(b, a, datos)
    return y

def transformar_audio(archivo_entrada, freq_objetivo):
    """Modula un archivo de audio a la frecuencia ultrasónica especificada."""
    ruta_entrada = os.path.join(CARPETA_ENTRADA, archivo_entrada)
    
    # Nombre y ruta de salida
    nombre_base = os.path.splitext(archivo_entrada)[0]
    nombre_salida = f"{nombre_base}_{freq_objetivo//1000}kHz.wav"
    ruta_salida = os.path.join(CARPETA_SALIDA, nombre_salida)

    # Si el archivo atacante ya existe, podemos saltarnos el proceso para ahorrar tiempo
    # (Comenta estas dos líneas si quieres forzar la sobreescritura siempre)
    if os.path.exists(ruta_salida):
        return ruta_salida

    try:
        datos, fs_original = sf.read(ruta_entrada)
        
        # Convertir a mono si es estéreo
        if len(datos.shape) > 1:
            datos = np.mean(datos, axis=1)

        # Remuestrear al SR objetivo (96 kHz)
        if fs_original != SAMPLE_RATE_SALIDA:
            datos = resample_poly(datos, SAMPLE_RATE_SALIDA, fs_original)

        # Normalizar y limpiar la señal base (mensaje)
        datos = datos / np.max(np.abs(datos))
        datos = filtro_paso_bajo(datos, 8000, SAMPLE_RATE_SALIDA)

        # Crear vector de tiempo y modular
        t = np.arange(len(datos)) / SAMPLE_RATE_SALIDA
        portadora = np.cos(2 * np.pi * freq_objetivo * t)
        senal_modulada = (1 + datos) * portadora
        
        # Normalizar salida
        senal_modulada = senal_modulada / np.max(np.abs(senal_modulada))
        
        # Guardar el archivo final en alta resolución
        sf.write(ruta_salida, senal_modulada, SAMPLE_RATE_SALIDA, subtype='FLOAT')
        return ruta_salida

    except Exception as e:
        print(f"[ERROR DSP] No se pudo modular el archivo: {e}")
        return None


# ==============================================================================
# BLOQUE 2: CONTROLADOR DE HARDWARE (HUMBIRD)
# ==============================================================================

class ControladorLaboratorio:
    def __init__(self, sistema_operativo, nombre_altavoz):
        self.sistema_operativo = sistema_operativo
        self.nombre_altavoz = nombre_altavoz

    def verificar_bluetooth(self):
        try:
            if self.sistema_operativo == "MacOS":
                resultado = subprocess.run(["system_profiler", "SPBluetoothDataType"], capture_output=True, text=True, timeout=10)
                return "Bluetooth Power: On" in resultado.stdout or "State: On" in resultado.stdout
            elif self.sistema_operativo == "Windows":
                resultado = subprocess.run(["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'}"], capture_output=True, text=True, timeout=10)
                return bool(resultado.stdout.strip())
            elif self.sistema_operativo == "Linux":
                resultado = subprocess.run(["bluetoothctl", "show"], capture_output=True, text=True, timeout=10)
                return "Powered: yes" in resultado.stdout
            return False
        except Exception:
            return False

    def conectar_altavoz(self):
        try:
            if self.sistema_operativo == "MacOS":
                resultado = subprocess.run(["blueutil", "--paired"], capture_output=True, text=True, timeout=10)
                direccion_mac = next((parte.split("address:")[1].strip() for linea in resultado.stdout.splitlines() if self.nombre_altavoz.lower() in linea.lower() for parte in linea.split(",") if "address:" in parte), None)
                if not direccion_mac: return False
                subprocess.run(["blueutil", "--connect", direccion_mac], timeout=30)
                time.sleep(2)
                verificacion = subprocess.run(["blueutil", "--is-connected", direccion_mac], capture_output=True, text=True, timeout=10)
                return verificacion.stdout.strip() == "1"
            elif self.sistema_operativo == "Windows":
                return True
            elif self.sistema_operativo == "Linux":
                resultado = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True, timeout=10)
                direccion_mac = next((linea.split()[1] for linea in resultado.stdout.splitlines() if self.nombre_altavoz.lower() in linea.lower()), None)
                if not direccion_mac: return False
                subprocess.run(["bluetoothctl", "connect", direccion_mac], timeout=15)
                return True
            return False
        except Exception:
            return False

    def ajustar_volumen(self, nivel=80):
        try:
            if self.sistema_operativo == "MacOS":
                subprocess.run(["osascript", "-e", f"set volume output volume {nivel}"], timeout=10)
            elif self.sistema_operativo == "Linux":
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{nivel}%"], timeout=10)
        except Exception:
            pass

    def reproducir_tono(self, ruta_archivo):
        try:
            datos, sample_rate = sf.read(ruta_archivo, dtype="float32")
            sd.play(datos, samplerate=sample_rate)
            sd.wait()  
        except Exception as e:
            print(f"[ERROR HW] Reproducción fallida: {e}")


# ==============================================================================
# BLOQUE 3: INTERFAZ GRÁFICA (GUI)
# ==============================================================================

class AplicacionLaboratorio:
    def __init__(self, root, controlador):
        self.root = root
        self.controlador = controlador
        self.reproduciendo = False

        self.root.title("Consola Ultrasónica - DuraMobi")
        self.root.geometry("450x350")
        
        self.crear_interfaz()
        self.root.protocol("WM_DELETE_WINDOW", self.al_cerrar)

        # Inicia el hardware automáticamente en segundo plano al abrir
        threading.Thread(target=self.auto_inicializar, daemon=True).start()

    def listar_archivos_originales(self):
        return sorted(f for f in os.listdir(CARPETA_ENTRADA) if f.lower().endswith(('.wav', '.mp3', '.flac')))

    def crear_interfaz(self):
        # Título y Estado
        tk.Label(self.root, text="LABORATORIO ACÚSTICO", font=("Courier", 18, "bold")).pack(pady=(20, 5))
        
        self.lbl_estado = tk.Label(self.root, text="Iniciando sistema (Bluetooth y Volumen)...", font=("Arial", 11, "italic"), fg="gray")
        self.lbl_estado.pack(pady=5)

        tk.Frame(self.root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=20, pady=10)

        # --- Selector de Archivos Originales ---
        marco_archivo = tk.Frame(self.root)
        marco_archivo.pack(pady=5)
        
        tk.Label(marco_archivo, text="Audio Base:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        archivos_base = self.listar_archivos_originales()
        if not archivos_base:
            archivos_base = ["(Sin archivos en /PruebasP)"]
            
        self.var_archivo = tk.StringVar(self.root)
        self.var_archivo.set(archivos_base[0])
        
        self.combo_archivo = tk.OptionMenu(marco_archivo, self.var_archivo, *archivos_base)
        self.combo_archivo.config(width=20)
        self.combo_archivo.pack(side=tk.LEFT, padx=5)

        # --- Selector de Frecuencia ---
        marco_freq = tk.Frame(self.root)
        marco_freq.pack(pady=5)
        
        tk.Label(marco_freq, text="Frecuencia (kHz):", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        frecuencias = ["18000", "19000", "20000"]
        self.var_freq = tk.StringVar(self.root)
        self.var_freq.set(frecuencias[1]) # 19kHz por defecto
        
        self.combo_freq = tk.OptionMenu(marco_freq, self.var_freq, *frecuencias)
        self.combo_freq.config(width=10)
        self.combo_freq.pack(side=tk.LEFT, padx=5)

        # --- Botones de Control ---
        marco_controles = tk.Frame(self.root)
        marco_controles.pack(pady=20)

        self.btn_play = tk.Button(marco_controles, text="▶ PLAY", font=("Arial", 12, "bold"), width=10, command=self.lanzar_ataque, state=tk.DISABLED)
        self.btn_play.pack(side=tk.LEFT, padx=10)

        self.btn_stop = tk.Button(marco_controles, text="■ STOP", font=("Arial", 12, "bold"), width=10, command=self.lanzar_stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

    def auto_inicializar(self):
        if not self.controlador.verificar_bluetooth():
            self.lbl_estado.config(text="Error: Bluetooth apagado.", fg="red")
            return

        self.lbl_estado.config(text="Conectando altavoz...", fg="blue")
        if not self.controlador.conectar_altavoz():
            self.lbl_estado.config(text="Error: Humbird no encontrado.", fg="red")
            return

        self.controlador.ajustar_volumen(VOLUMEN_SEGURO)
        self.lbl_estado.config(text="¡Hardware Listo! (Vol. 80%)", fg="green")
        self.btn_play.config(state=tk.NORMAL)

    def lanzar_ataque(self):
        archivo = self.var_archivo.get()
        if not archivo or "Sin archivos" in archivo:
            messagebox.showerror("Error", "Mete un audio válido en la carpeta 'PruebasP'.")
            return

        freq = int(self.var_freq.get())
        
        self.reproduciendo = True
        self.btn_play.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        # Iniciar el proceso en un hilo para no congelar la ventana
        threading.Thread(target=self.hilo_procesamiento_reproduccion, args=(archivo, freq), daemon=True).start()

    def hilo_procesamiento_reproduccion(self, archivo, freq):
        # 1. Modulación DSP
        self.root.after(0, lambda: self.lbl_estado.config(text=f"Modulando a {freq//1000}kHz...", fg="orange"))
        ruta_modulada = transformar_audio(archivo, freq)
        
        if not ruta_modulada:
            self.root.after(0, lambda: self.lbl_estado.config(text="Error en la modulación.", fg="red"))
            self.root.after(0, self.reset_botones)
            return

        # 2. Reproducción Hardware
        if self.reproduciendo: # Por si el usuario pulsó STOP durante la modulación
            self.root.after(0, lambda: self.lbl_estado.config(text=f"Emitiendo Ultrasonido: {freq//1000}kHz", fg="blue"))
            self.controlador.reproducir_tono(ruta_modulada)
        
        self.root.after(0, self.reset_botones)

    def lanzar_stop(self):
        self.reproduciendo = False
        sd.stop()  
        self.lbl_estado.config(text="Emisión abortada.", fg="red")
        self.reset_botones()

    def reset_botones(self):
        self.btn_play.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        if not self.reproduciendo:
            self.lbl_estado.config(text="¡Hardware Listo! (Vol. 80%)", fg="green")

    def al_cerrar(self):
        sd.stop()
        self.root.destroy()


if __name__ == "__main__":
    motor = ControladorLaboratorio(SISTEMA_ACTUAL, NOMBRE_ALTAVOZ)
    ventana = tk.Tk()
    app = AplicacionLaboratorio(ventana, motor)
    ventana.mainloop()