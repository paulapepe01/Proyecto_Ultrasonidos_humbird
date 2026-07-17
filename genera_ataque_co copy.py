
import tkinter as tk
from tkinter import ttk
import os
import numpy as np
import scipy.io as sio
import threading
import time

try:
    import libm2k
    LIBM2K_AVAILABLE = True
except ImportError:
    LIBM2K_AVAILABLE = False

# Flag para usar ADALM2000
ADALM_CONNECTED = False
ADALM_SELECT    = 0

# Parámetros globales
SIGNAL_SCALE = 1
ATTACK_FILE = ""
DATA_FOLDER = "./Datos/Ataque 750kHz"
N = 19
tam_buffer = 2 ** N
Fs = 750000
b1 = np.zeros(tam_buffer)
zeros = np.zeros(tam_buffer)
activate_attack = False
continuous_mode = False

# Inicialización del ADALM2000
ctx = None
aout = None
if ADALM_CONNECTED and LIBM2K_AVAILABLE:
    uris = libm2k.getAllContexts()
    for i, uri in enumerate(uris):
        print(f"{i}: {uri}")

    ctx = libm2k.m2kOpen(uris[ADALM_SELECT])  # o uris[1], etc.
    print("Número de serie:", ctx.getSerialNumber())
          
    if ctx is None:
        print("Connection Error: No ADALM2000 device available/connected to your PC.")
        exit(1)

    ain = ctx.getAnalogIn()
    aout = ctx.getAnalogOut()
    trig = ain.getTrigger()
    ain.reset()
    aout.reset()
    ctx.calibrateADC()
    ctx.calibrateDAC()
    aout.setSampleRate(0, Fs)
    aout.setSampleRate(1, Fs)
    aout.enableChannel(0, True)
    aout.enableChannel(1, True)
    aout.setCyclic(False)

# Función para actualizar parámetros

def update_parameters(file_attack, atenuation):
    global SIGNAL_SCALE, ATTACK_FILE
    SIGNAL_SCALE = float(atenuation)
    ATTACK_FILE = file_attack

# Función para ejecutar el ataque


def ejecutar_ataque():
    global b1
    try:
        data_file_path = os.path.join(DATA_FOLDER, ATTACK_FILE)
        data = sio.loadmat(data_file_path)
        
        if 'signal_data' in data:
            datos = data['signal_data']
        else:
            datos = data['datos_t']

        modulated_signal = datos.flatten() * SIGNAL_SCALE
        length = len(modulated_signal)
        if length > tam_buffer:
            b1 = modulated_signal[0:length]
        else:
            b1[0:length] = modulated_signal
        if ADALM_CONNECTED and LIBM2K_AVAILABLE:
            aout.enableChannel(0, True)
            aout.enableChannel(1, True)
            aout.push(1, b1)
            aout.push(0, b1)
        print(f"Ataque ejecutado con archivo {ATTACK_FILE} y atenuación {SIGNAL_SCALE}")
    except Exception as e:
        print(f"Error al ejecutar el ataque con archivo '{ATTACK_FILE}': {e}")


# GUI con Tkinter

def get_files():
    return os.listdir(DATA_FOLDER)

def iniciar_ataque():
    global activate_attack, continuous_mode
    file_selected = combo_var.get()
    atenuation_selected = atenuation_entry.get()
    update_parameters(file_selected, atenuation_selected)
    continuous_mode = mode_var.get() == "Continuo"
    activate_attack = True

# Bucle de ejecución en hilo separado
        
def loop_ataque():
    global activate_attack
    while True:
        if activate_attack:
            ejecutar_ataque()
            if not continuous_mode:
                activate_attack = False
        time.sleep(0.1)


# Crear hilo para el bucle de ataque
threading.Thread(target=loop_ataque, daemon=True).start()

root = tk.Tk()
root.title("DISPLAY ATAQUE")
root.geometry("800x600")
root.configure(bg="#101010")

main_frame = tk.Frame(root, bg="#101010")
main_frame.pack(expand=True)



# Frame superior para los selectores
top_frame = tk.Frame(root, bg="#101010")
top_frame.pack(pady=20)

combo_var = tk.StringVar()
files = get_files()
combo_box = ttk.Combobox(main_frame, textvariable=combo_var, values=files, font=("OCR A Extended", 16), state="readonly", width=30)
combo_box.set("Select File")
combo_box.pack(side="left", padx=20, pady=10)

style = ttk.Style()
style.theme_use("clam")
style.configure("TCombobox", fieldbackground="101010", background="#101010", foreground="#FFFFFF")
style.map("TCombobox", fieldbackground=[("readonly", "#101010")], background=[("readonly", "#101010")], foreground=[("readonly", "#FFFFFF")])

atenuation_label = tk.Label(main_frame, text="Atenuation:", fg="#FFFFFF", bg="#101010", font=("OCR A Extrended", 16))
atenuation_label.pack(side="left", padx=10)

atenuation_var = tk.StringVar()
atenuation_entry = tk.Entry(main_frame, textvariable=atenuation_var, font=("OCR A Extrended", 16), fg="#FFFFFF", bg="#101010", width=5)
atenuation_entry.pack(side="left", padx=10)

mode_var = tk.StringVar(value="Puntual")
mode_selector = ttk.Combobox(main_frame, textvariable=mode_var, values=["Puntual", "Continuo"], font=("OCR A Extended", 16), state="readonly", width=10)
mode_selector.pack(side="left", padx=10)

#button = tk.Button(main_frame, text="Ataque", font=("OCR A Extended", 16), fg="#FFFFFF", bg="#101010", command=iniciar_ataque)
#button.pack(side="left", padx=20)


# Crear un frame separado para el botón debajo del frame principal
# button_frame = tk.Frame(root, bg="#101010")
# button_frame.pack(pady=10)

# button.pack(in_=button_frame)



# Crear un frame separado para el botón debajo del frame principal
button_frame = tk.Frame(root, bg="#101010")
button_frame.pack(pady=10)

button = tk.Button(button_frame, text="Ataque", font=("OCR A Extended", 16), fg="#FFFFFF", bg="#101010", command=iniciar_ataque)
button.pack(in_=button_frame)


def close_fullscreen(event):
    root.attributes('-fullscreen', False)

root.bind("<Escape>", close_fullscreen)
root.mainloop()

if ADALM_CONNECTED and LIBM2K_AVAILABLE:
    libm2k.contextClose(ctx)
