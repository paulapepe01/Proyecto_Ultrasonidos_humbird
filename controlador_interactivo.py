"""
================================================================================
 CONTROL DE EMISIÓN ACÚSTICA - DuraMobi Humbird
 Interfaz gráfica de laboratorio (Tkinter) para pruebas de transductor de
 conducción por superficie con tonos WAV de alta frecuencia (18/20 kHz).
================================================================================

INSTALACIÓN PREVIA (TODOS LOS SISTEMAS OPERATIVOS) - Hacer UNA SOLA VEZ
--------------------------------------------------------------------------
Para la reproducción de audio bit-perfecta se necesitan las librerías
'sounddevice' y 'soundfile'. Instálalas con pip (funciona igual en
MacOS, Windows y Linux):

    pip3 install sounddevice soundfile

En MacOS y Linux, 'sounddevice' depende de una librería del sistema
llamada 'portaudio'. Si al ejecutar el script aparece un error tipo
"OSError: PortAudio library not found", instálala así:

    MacOS:  brew install portaudio
    Linux:  sudo apt install libportaudio2

En Windows normalmente no hace falta ningún paso extra: pip ya incluye
los binarios necesarios de PortAudio.

INSTALACIÓN PREVIA (SOLO MacOS)
--------------------------------------------------------------------------
macOS no tiene comando nativo para conectar Bluetooth por terminal,
por eso se necesita 'blueutil'.

1. Instalar Homebrew (si no lo tienes, prueba con: brew --version):
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
2. Instalar blueutil:
   brew install blueutil
3. Verificar que funciona (debe listar tus dispositivos emparejados):
   blueutil --paired
4. Si el script no encuentra blueutil, buscar la ruta con:
   which blueutil
   y usar esa ruta completa en vez de solo "blueutil".

INSTALACIÓN PREVIA (SOLO Windows)
--------------------------------------------------------------------------
1. Verificar que PowerShell está disponible (viene preinstalado):
   powershell -Command "Get-Host"
2. Para conectar el altavoz automáticamente, instalar el módulo
   'BluetoothCLI' o similar (requiere permisos de administrador), desde
   PowerShell como Administrador:
   Install-Module -Name BluetoothCLI -Scope CurrentUser
3. Si falla, conecta el altavoz manualmente desde:
   Configuración > Dispositivos > Bluetooth y otros dispositivos
4. El ajuste automático de volumen requiere 'nircmd' o 'pycaw'. Sin ellas,
   la aplicación avisará y habrá que ajustar el volumen a mano.

INSTALACIÓN PREVIA (SOLO Linux)
--------------------------------------------------------------------------
1. Instalar bluez (Debian/Ubuntu):
   sudo apt update && sudo apt install bluez
2. Verificar instalación:
   bluetoothctl --version
3. Ver dispositivos conocidos:
   bluetoothctl show
   bluetoothctl devices
4. Instalar alsa-utils para el control de volumen:
   sudo apt install alsa-utils
================================================================================
"""

import os
import sys
import io
import platform
import threading
import time
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import sounddevice as sd
import soundfile as sf


# ==============================================================================
# MOTOR LÓGICO (BACKEND) — SIN MODIFICAR
# ==============================================================================
SISTEMAS_OP = ["MacOS", "Windows", "Linux"]


class ControladorLaboratorio:
    """
    Clase encargada de gestionar las pruebas acústicas del transductor
    DuraMobi Humbird. Incluye verificación de Bluetooth, conexión al
    altavoz, ajuste de volumen por seguridad del hardware y reproducción
    bit-perfecta del tono de prueba.
    """

    def __init__(self, sistema_operativo, nombre_altavoz):
        self.sistema_operativo = sistema_operativo
        self.nombre_altavoz = nombre_altavoz

    def verificar_bluetooth(self):
        """
        Verifica si el Bluetooth está encendido usando comandos nativos
        de terminal según el sistema operativo configurado.
        """
        print(f"[INFO] Verificando estado de Bluetooth en {self.sistema_operativo}...")

        try:
            if self.sistema_operativo == "MacOS":
                resultado = subprocess.run(
                    ["system_profiler", "SPBluetoothDataType"],
                    capture_output=True, text=True, timeout=10
                )
                salida = resultado.stdout
                if "Bluetooth Power: On" in salida or "State: On" in salida:
                    return True
                elif "Bluetooth Power: Off" in salida or "State: Off" in salida:
                    return False
                else:
                    print("[AVISO] No se pudo determinar el estado con certeza. Revisa manualmente.")
                    return False

            elif self.sistema_operativo == "Windows":
                resultado = subprocess.run(
                    ["powershell", "-Command",
                     "Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'}"],
                    capture_output=True, text=True, timeout=10
                )
                return bool(resultado.stdout.strip())

            elif self.sistema_operativo == "Linux":
                resultado = subprocess.run(
                    ["bluetoothctl", "show"],
                    capture_output=True, text=True, timeout=10
                )
                return "Powered: yes" in resultado.stdout

            else:
                print("[ERROR] Sistema operativo no reconocido en la lista SISTEMAS_OP.")
                return False

        except FileNotFoundError:
            print("[ERROR] No se encontró el comando necesario para verificar Bluetooth en este sistema.")
            return False
        except subprocess.TimeoutExpired:
            print("[ERROR] El comando tardó demasiado en responder.")
            return False

    def conectar_altavoz(self):
        """
        Conecta el altavoz Bluetooth (Humbird) usando su nombre, siempre
        y cuando ya esté PREVIAMENTE EMPAREJADO (pairing) con el equipo
        desde la configuración normal del sistema operativo.

        Este método NO empareja dispositivos nuevos (eso requiere confirmación
        manual del PIN/código la primera vez), solo conecta uno ya conocido.
        """
        print(f"[INFO] Intentando conectar con el altavoz '{self.nombre_altavoz}'...")

        try:
            if self.sistema_operativo == "MacOS":
                resultado = subprocess.run(
                    ["blueutil", "--paired"],
                    capture_output=True, text=True, timeout=10
                )

                direccion_mac = None
                for linea in resultado.stdout.splitlines():
                    if self.nombre_altavoz.lower() in linea.lower():
                        partes = linea.split(",")
                        for parte in partes:
                            if "address:" in parte:
                                direccion_mac = parte.split("address:")[1].strip()

                if not direccion_mac:
                    print(f"[ERROR] No se encontró '{self.nombre_altavoz}' en los dispositivos emparejados.")
                    print("        Verifica que el nombre coincida exactamente y que esté emparejado antes.")
                    return False

                subprocess.run(["blueutil", "--connect", direccion_mac], timeout=30)
                time.sleep(3)

                verificacion = subprocess.run(
                    ["blueutil", "--is-connected", direccion_mac],
                    capture_output=True, text=True, timeout=10
                )
                if verificacion.stdout.strip() == "1":
                    print(f"[OK] Altavoz '{self.nombre_altavoz}' conectado correctamente.")
                    return True
                else:
                    print(f"[ERROR] No se pudo confirmar la conexión con '{self.nombre_altavoz}'.")
                    return False

            elif self.sistema_operativo == "Windows":
                print("[AVISO] La conexión automática en Windows requiere herramientas adicionales")
                print("        (ej. 'BluetoothCLI' o scripts con la API de Windows.Devices.Bluetooth).")
                print("        Por ahora, conecta el altavoz manualmente desde Configuración > Bluetooth.")
                return False

            elif self.sistema_operativo == "Linux":
                resultado = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True, text=True, timeout=10
                )

                direccion_mac = None
                for linea in resultado.stdout.splitlines():
                    if self.nombre_altavoz.lower() in linea.lower():
                        direccion_mac = linea.split()[1]

                if not direccion_mac:
                    print(f"[ERROR] No se encontró '{self.nombre_altavoz}' en los dispositivos conocidos.")
                    return False

                subprocess.run(["bluetoothctl", "connect", direccion_mac], timeout=15)
                print(f"[OK] Comando de conexión enviado para '{self.nombre_altavoz}'.")
                return True

            else:
                print("[ERROR] Sistema operativo no reconocido en la lista SISTEMAS_OP.")
                return False

        except FileNotFoundError as e:
            print(f"[ERROR] Falta una herramienta necesaria: {e}")
            print("        Revisa las instrucciones de instalación según tu sistema operativo.")
            return False
        except subprocess.TimeoutExpired:
            print("[ERROR] El comando de conexión tardó demasiado en responder.")
            return False

    def ajustar_volumen(self, nivel=50):
        """
        Ajusta el volumen general del sistema al nivel indicado (por defecto 50%).
        Esto es crítico por seguridad: al 100% el altavoz de conducción por
        superficie puede saturar mecánicamente, generando traqueteo que
        arruina la toma de datos.
        """
        print(f"[INFO] Ajustando volumen del sistema a {nivel}%...")

        try:
            if self.sistema_operativo == "MacOS":
                resultado = subprocess.run(
                    ["osascript", "-e", f"set volume output volume {nivel}"],
                    capture_output=True, text=True, timeout=10
                )
                if resultado.returncode == 0:
                    print(f"[OK] Volumen ajustado a {nivel}%.")
                    return True
                else:
                    print(f"[ERROR] No se pudo ajustar el volumen: {resultado.stderr}")
                    return False

            elif self.sistema_operativo == "Windows":
                print("[AVISO] Ajuste automático de volumen en Windows requiere")
                print("        una herramienta adicional (ej. nircmd o pycaw).")
                print(f"        Ajusta manualmente el volumen a {nivel}% antes de continuar.")
                return False

            elif self.sistema_operativo == "Linux":
                resultado = subprocess.run(
                    ["amixer", "-D", "pulse", "sset", "Master", f"{nivel}%"],
                    capture_output=True, text=True, timeout=10
                )
                if resultado.returncode == 0:
                    print(f"[OK] Volumen ajustado a {nivel}%.")
                    return True
                else:
                    print(f"[ERROR] No se pudo ajustar el volumen: {resultado.stderr}")
                    return False

            else:
                print("[ERROR] Sistema operativo no reconocido en la lista SISTEMAS_OP.")
                return False

        except FileNotFoundError as e:
            print(f"[ERROR] Falta una herramienta necesaria: {e}")
            return False
        except subprocess.TimeoutExpired:
            print("[ERROR] El comando de ajuste de volumen tardó demasiado en responder.")
            return False

    def reproducir_tono(self, ruta_archivo):
        """
        Lee un archivo de audio (.wav) extrayendo sus datos y su Sample Rate
        NATIVO con soundfile, y lo reproduce con sounddevice sin resampling,
        garantizando transmisión bit-perfecta al DAC. Espera a que termine
        antes de continuar.
        """
        print(f"[INFO] Cargando archivo de audio: {ruta_archivo}...")

        try:
            datos, sample_rate = sf.read(ruta_archivo, dtype="float32")

            print(f"[INFO] Sample Rate detectado: {sample_rate} Hz")
            print(f"[INFO] Duración: {len(datos) / sample_rate:.2f} segundos")
            print("[INFO] Reproduciendo tono de prueba...")

            sd.play(datos, samplerate=sample_rate)
            sd.wait()

            print("[OK] Reproducción finalizada.")
            return True

        except FileNotFoundError:
            print(f"[ERROR] No se encontró el archivo '{ruta_archivo}'. Verifica la ruta.")
            return False
        except Exception as e:
            print(f"[ERROR] Ocurrió un problema durante la reproducción: {e}")
            return False


# ==============================================================================
# INTERFAZ GRÁFICA (GUI)
# ==============================================================================

# Paleta "instrumentación de laboratorio"
COLOR_FONDO = "#101010"
COLOR_PANEL = "#181818"
COLOR_BORDE = "#2A2A2A"
COLOR_TEXTO = "#FFFFFF"
COLOR_TEXTO_SEC = "#9A9A9A"
COLOR_ACENTO = "#00CFFF"
COLOR_OK = "#00FF66"
COLOR_ERROR = "#FF4444"
COLOR_AVISO = "#FFAA00"
COLOR_LED_APAGADO = "#3A3A3A"

CARPETA_AUDIOS = "AUDIOS"


def _fuente_disponible():
    """
    Intenta usar 'OCR A Extended' (fuente típica de instrumentación de
    laboratorio). Si no está instalada en el sistema, Tk simplemente cae de
    vuelta a una tipografía monoespaciada estándar sin lanzar error.
    """
    return "OCR A Extended"


class AppLaboratorio(tk.Tk):
    """
    Aplicación principal. Envuelve ControladorLaboratorio (motor lógico, sin
    modificar) en una interfaz gráfica multihilo: la conexión Bluetooth y la
    reproducción de audio se ejecutan en hilos secundarios para que el
    mainloop de Tkinter nunca se congele.
    """

    def __init__(self):
        super().__init__()

        self.title("LAB. ACÚSTICO — DuraMobi Humbird — Panel de Control")
        self.configure(bg=COLOR_FONDO)
        self.geometry("620x560")
        self.minsize(620, 560)

        self.font_normal = (_fuente_disponible(), 10)
        self.font_bold = (_fuente_disponible(), 11, "bold")
        self.font_titulo = (_fuente_disponible(), 15, "bold")
        self.font_mono_log = (_fuente_disponible(), 9)

        # --- Estado interno ---
        self.controlador = None
        self.datos_audio = None
        self.sample_rate = None
        self.reproduciendo = False
        self.hilo_reproduccion = None

        self._configurar_estilo_ttk()
        self._construir_ui()
        self._refrescar_lista_wav()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --------------------------------------------------------------------
    # CONSTRUCCIÓN DE LA INTERFAZ
    # --------------------------------------------------------------------
    def _configurar_estilo_ttk(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")

        estilo.configure(
            "Lab.TCombobox",
            fieldbackground=COLOR_PANEL,
            background=COLOR_PANEL,
            foreground=COLOR_TEXTO,
            arrowcolor=COLOR_ACENTO,
            bordercolor=COLOR_BORDE,
            lightcolor=COLOR_PANEL,
            darkcolor=COLOR_PANEL,
            selectbackground=COLOR_PANEL,
            selectforeground=COLOR_TEXTO,
            padding=4,
        )
        self.option_add("*TCombobox*Listbox.background", COLOR_PANEL)
        self.option_add("*TCombobox*Listbox.foreground", COLOR_TEXTO)
        self.option_add("*TCombobox*Listbox.selectBackground", COLOR_ACENTO)
        self.option_add("*TCombobox*Listbox.font", self.font_normal)

        estilo.configure(
            "Lab.Horizontal.TProgressbar",
            troughcolor=COLOR_PANEL,
            background=COLOR_ACENTO,
            bordercolor=COLOR_BORDE,
        )

    def _seccion(self, padre, titulo):
        marco = tk.LabelFrame(
            padre, text=titulo, bg=COLOR_FONDO, fg=COLOR_ACENTO,
            font=self.font_bold, bd=1, relief="solid",
            labelanchor="nw", padx=10, pady=8,
            highlightbackground=COLOR_BORDE,
        )
        return marco

    def _fila(self, padre, etiqueta):
        fila = tk.Frame(padre, bg=COLOR_FONDO)
        fila.pack(fill="x", pady=4)
        lbl = tk.Label(
            fila, text=etiqueta, bg=COLOR_FONDO, fg=COLOR_TEXTO_SEC,
            font=self.font_normal, width=18, anchor="w"
        )
        lbl.pack(side="left")
        return fila

    def _construir_ui(self):
        # --- Cabecera ---
        cabecera = tk.Frame(self, bg=COLOR_FONDO)
        cabecera.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(
            cabecera, text="◆ PANEL DE EMISIÓN ACÚSTICA — DuraMobi Humbird",
            bg=COLOR_FONDO, fg=COLOR_TEXTO, font=self.font_titulo
        ).pack(side="left")

        # --- Panel de configuración ---
        panel_config = self._seccion(self, "CONFIGURACIÓN DE ENSAYO")
        panel_config.pack(fill="x", padx=16, pady=6)

        # Sistema operativo
        fila_so = self._fila(panel_config, "Sistema Operativo:")
        self.combo_sistema = ttk.Combobox(
            fila_so, values=SISTEMAS_OP, state="readonly",
            style="Lab.TCombobox", font=self.font_normal, width=30
        )
        self.combo_sistema.pack(side="left", fill="x", expand=True)
        self.combo_sistema.set(self._detectar_sistema_actual())

        # Archivo WAV
        fila_wav = self._fila(panel_config, "Archivo WAV:")
        self.combo_archivo = ttk.Combobox(
            fila_wav, values=[], state="readonly",
            style="Lab.TCombobox", font=self.font_normal, width=24
        )
        self.combo_archivo.pack(side="left", fill="x", expand=True)
        tk.Button(
            fila_wav, text="⟳", command=self._refrescar_lista_wav,
            bg=COLOR_PANEL, fg=COLOR_ACENTO, activebackground=COLOR_BORDE,
            activeforeground=COLOR_ACENTO, font=self.font_bold, relief="flat",
            width=3, cursor="hand2"
        ).pack(side="left", padx=(6, 0))

        # Modo de emisión
        fila_modo = self._fila(panel_config, "Modo de Emisión:")
        self.combo_modo = ttk.Combobox(
            fila_modo, values=["Puntual", "Continuo"], state="readonly",
            style="Lab.TCombobox", font=self.font_normal, width=30
        )
        self.combo_modo.pack(side="left", fill="x", expand=True)
        self.combo_modo.set("Puntual")

        # Nombre del altavoz
        fila_alt = self._fila(panel_config, "Altavoz (BT):")
        self.entry_altavoz = tk.Entry(
            fila_alt, bg=COLOR_PANEL, fg=COLOR_TEXTO, insertbackground=COLOR_TEXTO,
            font=self.font_normal, relief="flat", highlightthickness=1,
            highlightbackground=COLOR_BORDE, highlightcolor=COLOR_ACENTO
        )
        self.entry_altavoz.pack(side="left", fill="x", expand=True, ipady=3)
        self.entry_altavoz.insert(0, "Humbird Speaker")

        # Volumen seguro
        fila_vol = self._fila(panel_config, "Volumen Seguro (%):")
        self.spin_volumen = tk.Spinbox(
            fila_vol, from_=0, to=100, bg=COLOR_PANEL, fg=COLOR_TEXTO,
            insertbackground=COLOR_TEXTO, font=self.font_normal, relief="flat",
            width=6, justify="center", highlightthickness=1,
            highlightbackground=COLOR_BORDE, highlightcolor=COLOR_ACENTO
        )
        self.spin_volumen.pack(side="left")
        self.spin_volumen.delete(0, "end")
        self.spin_volumen.insert(0, "50")

        # --- Panel de estado (LEDs) ---
        panel_estado = self._seccion(self, "ESTADO DEL SISTEMA")
        panel_estado.pack(fill="x", padx=16, pady=6)

        fila_leds = tk.Frame(panel_estado, bg=COLOR_FONDO)
        fila_leds.pack(fill="x", pady=2)

        self.led_bt, _ = self._crear_led(fila_leds, "BLUETOOTH")
        self.led_conn, _ = self._crear_led(fila_leds, "ALTAVOZ")
        self.led_vol, _ = self._crear_led(fila_leds, "VOLUMEN")
        self.led_audio, _ = self._crear_led(fila_leds, "AUDIO CARGADO")

        self.label_estado = tk.Label(
            panel_estado, text="Sistema en espera. Pulsa ATAQUE para iniciar.",
            bg=COLOR_FONDO, fg=COLOR_TEXTO_SEC, font=self.font_normal, anchor="w"
        )
        self.label_estado.pack(fill="x", pady=(8, 0))

        # --- Botones de control ---
        panel_botones = tk.Frame(self, bg=COLOR_FONDO)
        panel_botones.pack(fill="x", padx=16, pady=10)

        self.btn_ataque = self._crear_boton(
            panel_botones, "⚡ ATAQUE", self._on_ataque, COLOR_ACENTO
        )
        self.btn_play = self._crear_boton(
            panel_botones, "▶ PLAY", self._on_play, COLOR_OK, activo=False
        )
        self.btn_pausa = self._crear_boton(
            panel_botones, "■ PAUSA / STOP", self._on_pausa, COLOR_ERROR, activo=False
        )

        for b in (self.btn_ataque, self.btn_play, self.btn_pausa):
            b.pack(side="left", expand=True, fill="x", padx=4)

        # --- Consola de log ---
        panel_log = self._seccion(self, "REGISTRO DE OPERACIONES")
        panel_log.pack(fill="both", expand=True, padx=16, pady=(6, 14))

        self.log = ScrolledText(
            panel_log, bg="#0A0A0A", fg="#33FF88", insertbackground="#33FF88",
            font=self.font_mono_log, relief="flat", wrap="word", height=10,
            state="disabled"
        )
        self.log.pack(fill="both", expand=True)

    def _crear_led(self, padre, etiqueta):
        marco = tk.Frame(padre, bg=COLOR_FONDO)
        marco.pack(side="left", expand=True, fill="x")
        canvas = tk.Canvas(
            marco, width=16, height=16, bg=COLOR_FONDO, highlightthickness=0
        )
        oid = canvas.create_oval(2, 2, 14, 14, fill=COLOR_LED_APAGADO, outline="")
        canvas.pack()
        tk.Label(
            marco, text=etiqueta, bg=COLOR_FONDO, fg=COLOR_TEXTO_SEC,
            font=(_fuente_disponible(), 8)
        ).pack()
        canvas._oval_id = oid
        return canvas, oid

    def _crear_boton(self, padre, texto, comando, color, activo=True):
        boton = tk.Button(
            padre, text=texto, command=comando, font=self.font_bold,
            bg=color if activo else COLOR_PANEL,
            fg="#101010" if activo else COLOR_TEXTO_SEC,
            activebackground=color, activeforeground="#101010",
            relief="flat", bd=0, pady=10, cursor="hand2",
            state="normal" if activo else "disabled"
        )
        return boton

    def _detectar_sistema_actual(self):
        so = platform.system()
        if so == "Darwin":
            return "MacOS"
        if so == "Windows":
            return "Windows"
        if so == "Linux":
            return "Linux"
        return SISTEMAS_OP[0]

    # --------------------------------------------------------------------
    # UTILIDADES DE UI (siempre invocadas desde el hilo principal vía after)
    # --------------------------------------------------------------------
    def _log_texto(self, texto):
        if not texto:
            return
        self.log.configure(state="normal")
        self.log.insert("end", texto if texto.endswith("\n") else texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_estado(self, texto, color=COLOR_TEXTO_SEC):
        self.label_estado.configure(text=texto, fg=color)

    def _set_led(self, canvas, encendido, color_ok=COLOR_OK, color_error=COLOR_ERROR):
        color = color_ok if encendido else color_error
        canvas.itemconfig(canvas._oval_id, fill=color)

    def _apagar_led(self, canvas):
        canvas.itemconfig(canvas._oval_id, fill=COLOR_LED_APAGADO)

    def _set_boton(self, boton, activo, color):
        boton.configure(
            state="normal" if activo else "disabled",
            bg=color if activo else COLOR_PANEL,
            fg="#101010" if activo else COLOR_TEXTO_SEC,
        )

    def _toggle_botones(self, ataque, play, pausa):
        self._set_boton(self.btn_ataque, ataque, COLOR_ACENTO)
        self._set_boton(self.btn_play, play, COLOR_OK)
        self._set_boton(self.btn_pausa, pausa, COLOR_ERROR)

    def _refrescar_lista_wav(self):
        archivos = []
        if os.path.isdir(CARPETA_AUDIOS):
            archivos = sorted(
                f for f in os.listdir(CARPETA_AUDIOS) if f.lower().endswith(".wav")
            )
        self.combo_archivo["values"] = archivos
        if archivos:
            self.combo_archivo.current(0)
        else:
            self.combo_archivo.set("")
            self._log_texto(f"[AVISO] No se encontraron archivos .wav en '{CARPETA_AUDIOS}/'.")

    # --------------------------------------------------------------------
    # CAPTURA DE LOS print() DEL BACKEND, SIN MODIFICAR ControladorLaboratorio
    # --------------------------------------------------------------------
    def _ejecutar_capturando_log(self, func, *args, **kwargs):
        """
        Redirige temporalmente stdout a un buffer para capturar los print()
        del backend y volcarlos a la consola gráfica. Se usa siempre desde
        el hilo secundario de trabajo (nunca hay dos llamadas concurrentes).
        """
        buffer = io.StringIO()
        stdout_original = sys.stdout
        sys.stdout = buffer
        try:
            resultado = func(*args, **kwargs)
        finally:
            sys.stdout = stdout_original
        texto = buffer.getvalue()
        if texto:
            self.after(0, self._log_texto, texto.rstrip("\n"))
        return resultado

    # --------------------------------------------------------------------
    # BOTÓN "ATAQUE" — inicializa hardware y carga el audio en memoria
    # --------------------------------------------------------------------
    def _on_ataque(self):
        archivo = self.combo_archivo.get()
        if not archivo:
            messagebox.showerror("Error", "Selecciona un archivo .wav antes de continuar.")
            return

        self._toggle_botones(ataque=False, play=False, pausa=False)
        for led in (self.led_bt, self.led_conn, self.led_vol, self.led_audio):
            self._apagar_led(led)
        self._set_estado("Ejecutando secuencia de ATAQUE...", COLOR_AVISO)
        self._log_texto("\n===== SECUENCIA DE ATAQUE INICIADA =====")

        hilo = threading.Thread(target=self._trabajo_ataque, args=(archivo,), daemon=True)
        hilo.start()

    def _trabajo_ataque(self, archivo):
        sistema = self.combo_sistema.get()
        nombre_altavoz = self.entry_altavoz.get().strip() or "Humbird Speaker"
        try:
            nivel_volumen = int(self.spin_volumen.get())
        except ValueError:
            nivel_volumen = 50

        self.controlador = ControladorLaboratorio(sistema, nombre_altavoz)

        # Paso 1: Bluetooth
        bt_ok = self._ejecutar_capturando_log(self.controlador.verificar_bluetooth)
        self.after(0, self._set_led, self.led_bt, bt_ok)
        if not bt_ok:
            self.after(0, self._set_estado, "DETENIDO: Bluetooth apagado o no verificable.", COLOR_ERROR)
            self.after(0, self._toggle_botones, True, False, False)
            return

        # Paso 2: Conexión al altavoz
        conectado = self._ejecutar_capturando_log(self.controlador.conectar_altavoz)
        self.after(0, self._set_led, self.led_conn, conectado)
        if not conectado:
            self.after(0, self._set_estado, "DETENIDO: no se pudo conectar el altavoz.", COLOR_ERROR)
            self.after(0, self._toggle_botones, True, False, False)
            return

        # Paso 3: Volumen seguro
        volumen_ok = self._ejecutar_capturando_log(self.controlador.ajustar_volumen, nivel_volumen)
        self.after(0, self._set_led, self.led_vol, volumen_ok)
        if not volumen_ok:
            self.after(0, self._log_texto, "[AVISO] Verifica el volumen manualmente antes de emitir.")

        # Paso 4: Cargar el WAV en memoria (bit-perfecto, sample rate nativo)
        ruta = os.path.join(CARPETA_AUDIOS, archivo)
        try:
            datos, sample_rate = sf.read(ruta, dtype="float32")
            self.datos_audio = datos
            self.sample_rate = sample_rate
            self.after(0, self._set_led, self.led_audio, True)
            self.after(
                0, self._log_texto,
                f"[OK] '{archivo}' cargado en memoria ({sample_rate} Hz, "
                f"{len(datos) / sample_rate:.2f} s)."
            )
            self.after(0, self._set_estado, "Sistema LISTO — preparado para emitir.", COLOR_OK)
            self.after(0, self._toggle_botones, True, True, False)
        except Exception as e:
            self.datos_audio = None
            self.sample_rate = None
            self.after(0, self._set_led, self.led_audio, False)
            self.after(0, self._log_texto, f"[ERROR] No se pudo cargar el archivo: {e}")
            self.after(0, self._set_estado, "Error al cargar el archivo de audio.", COLOR_ERROR)
            self.after(0, self._toggle_botones, True, False, False)

    # --------------------------------------------------------------------
    # BOTÓN "PLAY" — reproduce en hilo secundario (Puntual o Continuo)
    # --------------------------------------------------------------------
    def _on_play(self):
        if self.datos_audio is None or self.sample_rate is None:
            messagebox.showwarning("Aviso", "Pulsa ATAQUE primero para cargar el audio.")
            return
        if self.reproduciendo:
            return

        modo = self.combo_modo.get()
        self.reproduciendo = True
        self._toggle_botones(ataque=False, play=False, pausa=True)
        self._set_estado(f"Emitiendo tono — modo {modo.upper()}...", COLOR_ACENTO)
        self._log_texto(f"[INFO] Iniciando reproducción en modo '{modo}'.")

        self.hilo_reproduccion = threading.Thread(
            target=self._trabajo_reproduccion, args=(modo,), daemon=True
        )
        self.hilo_reproduccion.start()

    def _trabajo_reproduccion(self, modo):
        en_bucle = (modo == "Continuo")
        try:
            # sd.play() es no bloqueante: el propio motor de PortAudio gestiona
            # la emisión (y el bucle, si loop=True) en segundo plano. Se lanza
            # desde este hilo para no interferir nunca con el mainloop de Tk.
            sd.play(self.datos_audio, samplerate=self.sample_rate, loop=en_bucle)

            if not en_bucle:
                sd.wait()  # bloquea SOLO este hilo secundario hasta terminar
                self.after(0, self._on_reproduccion_terminada, "Reproducción finalizada (Puntual).")
            # En modo Continuo el hilo termina aquí; el audio sigue sonando
            # en el motor de audio hasta que el usuario pulse PAUSA/STOP.
        except Exception as e:
            self.after(0, self._log_texto, f"[ERROR] Fallo durante la reproducción: {e}")
            self.after(0, self._on_reproduccion_terminada, "Error durante la reproducción.")

    def _on_reproduccion_terminada(self, mensaje):
        self.reproduciendo = False
        self._toggle_botones(ataque=True, play=True, pausa=False)
        self._set_estado(f"Sistema LISTO — {mensaje}", COLOR_OK)
        self._log_texto(f"[OK] {mensaje}")

    # --------------------------------------------------------------------
    # BOTÓN "PAUSA / STOP"
    # --------------------------------------------------------------------
    def _on_pausa(self):
        sd.stop()
        self.reproduciendo = False
        self._toggle_botones(ataque=True, play=True, pausa=False)
        self._set_estado("Emisión detenida por el usuario.", COLOR_AVISO)
        self._log_texto("[INFO] STOP solicitado por el usuario. sd.stop() ejecutado.")

    # --------------------------------------------------------------------
    # CIERRE LIMPIO
    # --------------------------------------------------------------------
    def _on_close(self):
        try:
            sd.stop()
        except Exception:
            pass
        self.reproduciendo = False
        # Los hilos se crean con daemon=True: al destruir la ventana y
        # terminar el proceso principal, Python los cierra automáticamente
        # sin dejar procesos huérfanos.
        self.destroy()


if __name__ == "__main__":
    app = AppLaboratorio()
    app.mainloop()