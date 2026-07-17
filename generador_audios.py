import numpy as np
from scipy.io.wavfile import write

# ==========================================================
# BLOQUE DE FRECUENCIAS DE PRUEBA (BARRIDO ESPACIADO)
# ----------------------------------------------------------
# Realizaremos un barrido desde 18 kHz hasta 44 kHz para mapear
# la pérdida de eficiencia (atenuación) del hardware de consumo.
#
# Descomenta (quita el '#') de la frecuencia que quieras generar:

# --- RANGO 1: NEAR-ULTRASOUND (Alta probabilidad de éxito en altavoces de consumo)
# FRECUENCIA = 18000   # 18 kHz - Borde audible / Near-ultrasound bajo
# FRECUENCIA = 19000   # 19 kHz - near-ultrasound típico (frecuencia actual de prueba)
# FRECUENCIA = 20000   # 20 kHz - Límite teórico de la audición humana

# --- RANGO 2: ULTRASOUND BAJO (Comportamiento inestable en tweeters comunes)
# FRECUENCIA = 25000   # 25 kHz - Punto de caída física para muchos tweeters de seda/plástico

# --- RANGO 3: ULTRASOUND MEDIO (Frecuencia típica de papers como DolphinAttack)
# FRECUENCIA = 30000   # 30 kHz - Aquí los filtros del DAC del PC suelen empezar a cortar
# FRECUENCIA = 35000   # 35 kHz - Límite de hardware especializado medio

# --- RANGO 4: ULTRASOUND ALTO (Frontera del software a 96 kHz de muestreo)
# FRECUENCIA = 40000   # 40 kHz - Frecuencia de laboratorio (DolphinAttack original)
# FRECUENCIA = 44000   # 44 kHz - Límite práctico de Nyquist para demostrar el bloqueo total
# ==========================================================
FRECUENCIA = 24000
# ----------------------------------------------------------
# PARÁMETROS DE MUESTREO Y SEÑAL
# ----------------------------------------------------------

# Frecuencia de muestreo: 96000 Hz (96 kHz)
# Según el teorema de Nyquist, la frecuencia de muestreo debe ser
# al menos el doble de la frecuencia máxima que queremos representar.
# Con 96 kHz podemos representar correctamente frecuencias de hasta
# 48 kHz, dejando un margen amplio por encima de nuestro rango de
# interés (18-22 kHz), evitando aliasing y distorsión de la señal.
SAMPLE_RATE = 96000

# Duración del archivo de audio en segundos
DURACION_SEGUNDOS = 5

# Amplitud máxima admitida por un entero de 16 bits con signo
# (rango real: -32768 a 32767). Usamos 32767 como referencia.
AMPLITUD_MAXIMA_16BIT = 32767

# Factor de seguridad para evitar clipping (saturación).
# Multiplicamos la amplitud por 0.8 en lugar de 1.0 para dejar
# un margen de "headroom" del 20%. Esto evita que picos de la
# onda superen el rango representable en 16 bits, lo que causaría
# recorte (clipping) y generaría armónicos audibles no deseados
# que contaminarían la prueba.
FACTOR_SEGURIDAD = 0.8

# ----------------------------------------------------------
# GENERACIÓN DE LA ONDA SENOIDAL
# ----------------------------------------------------------

# Creamos el vector de tiempo: un array de instantes de muestreo
# equiespaciados, desde 0 hasta DURACION_SEGUNDOS.
# num_muestras = sample_rate * duración -> total de puntos discretos.
num_muestras = int(SAMPLE_RATE * DURACION_SEGUNDOS)

# np.linspace genera 'num_muestras' puntos entre 0 y la duración total.
# endpoint=False evita que la última muestra coincida exactamente con
# el instante final (lo que podría duplicar el punto 0 del siguiente ciclo).
tiempo = np.linspace(0, DURACION_SEGUNDOS, num_muestras, endpoint=False)

# Ecuación de la onda senoidal:
#   y(t) = A * sin(2 * pi * f * t)
# Donde:
#   A = amplitud (por ahora usamos 1.0, normalizada)
#   f = frecuencia en Hz (FRECUENCIA)
#   t = vector de tiempo
# 2*pi*f convierte la frecuencia en radianes/segundo (velocidad angular).
onda = np.sin(2 * np.pi * FRECUENCIA * tiempo)

# ----------------------------------------------------------
# ESCALADO Y CONVERSIÓN A PCM 16 BITS
# ----------------------------------------------------------

# Escalamos la onda (rango -1.0 a 1.0) al rango de un entero de 16 bits,
# aplicando el factor de seguridad para evitar saturación.
onda_escalada = onda * AMPLITUD_MAXIMA_16BIT * FACTOR_SEGURIDAD

# Convertimos a enteros de 16 bits con signo (int16), formato PCM
# estándar requerido por el archivo .wav.
onda_int16 = onda_escalada.astype(np.int16)

# ----------------------------------------------------------
# EXPORTACIÓN DEL ARCHIVO .WAV
# ----------------------------------------------------------

nombre_archivo = f"tono_{FRECUENCIA}Hz_{SAMPLE_RATE}Hz.wav"

# scipy.io.wavfile.write escribe el archivo en formato PCM 16 bits
# usando la frecuencia de muestreo y el array de enteros generado.
write(nombre_archivo, SAMPLE_RATE, onda_int16)

print(f"Archivo generado: {nombre_archivo}")
print(f"Frecuencia: {FRECUENCIA} Hz | Sample rate: {SAMPLE_RATE} Hz | Duración: {DURACION_SEGUNDOS}s")