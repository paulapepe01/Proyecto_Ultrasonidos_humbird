# ==============================================================================
# INSTALACIÓN PREVIA (TODOS LOS SISTEMAS OPERATIVOS) - Hacer UNA SOLA VEZ
# ==============================================================================
# Para la reproducción de audio bit-perfecta se necesitan las librerías
# 'sounddevice' y 'soundfile'. Instálalas con pip (funciona igual en
# MacOS, Windows y Linux):
#
#   pip3 install sounddevice soundfile
#
# En MacOS y Linux, 'sounddevice' depende de una librería del sistema
# llamada 'portaudio'. Si al ejecutar el script aparece un error tipo
# "OSError: PortAudio library not found", instálala así:
#
#   MacOS:  brew install portaudio
#   Linux:  sudo apt install libportaudio2
#
# En Windows normalmente no hace falta ningún paso extra: pip ya incluye
# los binarios necesarios de PortAudio.
# ==============================================================================


# ==============================================================================
# INSTALACIÓN PREVIA (SOLO MacOS) - Hacer UNA SOLA VEZ
# ==============================================================================
# macOS no tiene comando nativo para conectar Bluetooth por terminal,
# por eso se necesita 'blueutil'.
#
# 1. Instalar Homebrew (si no lo tienes, prueba con: brew --version):
#    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
#
# 2. Instalar blueutil:
#    brew install blueutil
#
# 3. Verificar que funciona (debe listar tus dispositivos emparejados):
#    blueutil --paired
#
# 4. Si el script no encuentra blueutil, buscar la ruta con:
#    which blueutil
#    y usar esa ruta completa en vez de solo "blueutil".
#
# El ajuste de volumen (osascript) NO requiere instalación, viene de fábrica.
# ==============================================================================


# ==============================================================================
# INSTALACIÓN PREVIA (SOLO Windows) - Hacer UNA SOLA VEZ
# ==============================================================================
# Windows trae PowerShell integrado, pero no permite conectar dispositivos
# Bluetooth ya emparejados directamente por comando de forma sencilla.
# La verificación de estado (encendido/apagado) SÍ funciona de fábrica con
# PowerShell, pero la CONEXIÓN automática requiere una herramienta extra.
#
# 1. Verificar que PowerShell está disponible (viene preinstalado):
#    powershell -Command "Get-Host"
#
# 2. Para conectar el altavoz automáticamente, instalar el módulo
#    'BluetoothCLI' o similar (requiere permisos de administrador):
#    Abrir PowerShell como Administrador y ejecutar:
#    Install-Module -Name BluetoothCLI -Scope CurrentUser
#
# 3. Si el punto 2 falla o no está disponible, la alternativa más fiable es
#    conectar el altavoz manualmente desde:
#    Configuración > Dispositivos > Bluetooth y otros dispositivos
#    (el script seguirá verificando el estado del Bluetooth, pero avisará
#    que la conexión debe hacerse a mano en Windows).
#
# 4. El ajuste automático de volumen requiere una herramienta adicional
#    como 'nircmd' o la librería 'pycaw'. Sin ellas, el script avisará
#    y habrá que ajustar el volumen manualmente al 50%.
# ==============================================================================


# ==============================================================================
# INSTALACIÓN PREVIA (SOLO Linux) - Hacer UNA SOLA VEZ
# ==============================================================================
# Linux necesita el paquete 'bluez', que incluye 'bluetoothctl', el comando
# usado para verificar y conectar dispositivos Bluetooth por terminal.
#
# 1. Instalar bluez (en distros basadas en Debian/Ubuntu):
#    sudo apt update
#    sudo apt install bluez
#
# 2. Verificar que se instaló correctamente:
#    bluetoothctl --version
#
# 3. Comprobar que el Bluetooth está encendido y ver dispositivos conocidos:
#    bluetoothctl show
#    bluetoothctl devices
#
# (En el paso 3 debería aparecer el "Humbird Speaker" si ya está emparejado)
#
# 4. El ajuste de volumen usa 'amixer', parte de alsa-utils. Si no lo tienes:
#    sudo apt install alsa-utils
# ==============================================================================

import os
import subprocess
import time
import sounddevice as sd
import soundfile as sf

# --- CONFIGURACIÓN MANUAL DEL ENTORNO ---
SISTEMAS_OP = ["MacOS", "Windows", "Linux"]
SISTEMA_ACTUAL = SISTEMAS_OP[0]  # Por defecto en MacOS. Cambia el índice según tu equipo.

# Nombre EXACTO del altavoz tal como aparece en tus dispositivos Bluetooth emparejados
NOMBRE_ALTAVOZ = "Humbird Speaker"  # Cambia esto según tu dispositivo.

# Nivel de volumen de seguridad para no saturar mecánicamente el transductor
VOLUMEN_SEGURO = 50

# Ruta/nombre del archivo de prueba a reproducir.
# Usamos os.path.join para que la ruta funcione perfectamente en Mac, Windows y Linux.
ARCHIVO_TONO = os.path.join("AUDIOS", "prueba.wav")


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
                # Requiere tener instalado 'blueutil' (ver instrucciones más arriba)
                # 1. Buscamos la dirección MAC del dispositivo emparejado por nombre
                resultado = subprocess.run(
                    ["blueutil", "--paired"],
                    capture_output=True, text=True, timeout=10
                )

                direccion_mac = None
                for linea in resultado.stdout.splitlines():
                    if self.nombre_altavoz.lower() in linea.lower():
                        # La línea tiene formato: address: xx-xx-xx-xx-xx-xx, ...
                        partes = linea.split(",")
                        for parte in partes:
                            if "address:" in parte:
                                direccion_mac = parte.split("address:")[1].strip()

                if not direccion_mac:
                    print(f"[ERROR] No se encontró '{self.nombre_altavoz}' en los dispositivos emparejados.")
                    print("        Verifica que el nombre coincida exactamente y que esté emparejado antes.")
                    return False

                # 2. Conectamos usando la dirección MAC encontrada
                subprocess.run(["blueutil", "--connect", direccion_mac], timeout=30)
                time.sleep(3)  # Pequeña espera para que la conexión se establezca

                # 3. Verificamos que realmente quedó conectado
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
                # bluetoothctl sí soporta conexión directa por dirección MAC
                resultado = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True, text=True, timeout=10
                )

                direccion_mac = None
                for linea in resultado.stdout.splitlines():
                    if self.nombre_altavoz.lower() in linea.lower():
                        # Formato: Device XX:XX:XX:XX:XX:XX NombreDispositivo
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
                # osascript controla el volumen del sistema vía AppleScript.
                # La escala interna de macOS es 0-100, coincide con nuestro "nivel".
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
                # Windows no tiene un comando nativo simple para fijar un %
                # exacto de volumen. Requiere una librería adicional (ej. pycaw)
                # o una utilidad externa como 'nircmd'. Por ahora se avisa.
                print("[AVISO] Ajuste automático de volumen en Windows requiere")
                print("        una herramienta adicional (ej. nircmd o pycaw).")
                print(f"        Ajusta manualmente el volumen a {nivel}% antes de continuar.")
                return False

            elif self.sistema_operativo == "Linux":
                # amixer (parte de alsa-utils) permite fijar el volumen del
                # canal maestro directamente por terminal.
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
            # Leemos los datos y el sample rate ORIGINAL del archivo (sin tocarlo)
            datos, sample_rate = sf.read(ruta_archivo, dtype="float32")

            print(f"[INFO] Sample Rate detectado: {sample_rate} Hz")
            print(f"[INFO] Duración: {len(datos) / sample_rate:.2f} segundos")
            print("[INFO] Reproduciendo tono de prueba...")

            # Reproducimos usando el sample_rate NATIVO leído del archivo,
            # nunca uno fijo, para evitar cualquier resampling automático
            sd.play(datos, samplerate=sample_rate)
            sd.wait()  # Bloquea la ejecución hasta que termine la reproducción

            print("[OK] Reproducción finalizada.")
            return True

        except FileNotFoundError:
            print(f"[ERROR] No se encontró el archivo '{ruta_archivo}'. Verifica la ruta.")
            return False
        except Exception as e:
            print(f"[ERROR] Ocurrió un problema durante la reproducción: {e}")
            return False


# --- BLOQUE PRINCIPAL DE PRUEBA ---
if __name__ == "__main__":
    controlador = ControladorLaboratorio(SISTEMA_ACTUAL, NOMBRE_ALTAVOZ)

    # Paso 1: Verificar que el Bluetooth esté encendido
    bluetooth_encendido = controlador.verificar_bluetooth()

    if not bluetooth_encendido:
        print("[DETENIDO] Bluetooth APAGADO o no verificable. Enciéndelo antes de continuar.")
    else:
        print("[OK] Bluetooth ENCENDIDO.")

        # Paso 2: Conectar el altavoz Humbird
        conectado = controlador.conectar_altavoz()

        if not conectado:
            print("[DETENIDO] No se pudo conectar el altavoz. Revisa la conexión manualmente.")
        else:
            # Paso 3: Ajustar el volumen al 50% por seguridad del hardware
            volumen_ajustado = controlador.ajustar_volumen(VOLUMEN_SEGURO)

            if not volumen_ajustado:
                print("[AVISO] No se pudo confirmar el ajuste de volumen. Verifica manualmente antes de continuar.")

            # Paso 4: Reproducir el tono de prueba (bit-perfecto)
            print("[LISTO] El sistema está preparado para iniciar la prueba acústica.")
            controlador.reproducir_tono(ARCHIVO_TONO)


            #cambio