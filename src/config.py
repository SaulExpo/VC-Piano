import numpy as np


SAMPLE_RATE = 44100
FREQUENCIES = {
    "DO": 261.63, "DO#": 277.18, "RE": 293.66, "RE#": 311.13,
    "MI": 329.63, "FA": 349.23, "FA#": 369.99, "SOL": 392.00,
    "SOL#": 415.30, "LA": 440.00, "LA#": 466.16, "SI": 493.88, "DO2": 523.25
}
ALL_NOTES = ["DO","DO#","RE","RE#","MI","FA","FA#","SOL","SOL#","LA","LA#","SI","DO2"]
WHITE_NOTES = ["DO", "RE", "MI", "FA", "SOL", "LA", "SI", "DO2"]
BLACK_NOTES_MAP = [(0, "DO#"), (1, "RE#"), (3, "FA#"), (4, "SOL#"), (5, "LA#")]

# --- GRÁFICOS ---
IMG_SIZE = (800, 300)
BLACK_NOTE_WIDTH_RATIO = 0.6
BLACK_NOTE_HEIGHT_RATIO = 0.5
TRANSPARENCY_ALPHA = 0.4 # 0.0 invisible, 1.0 totalmente opaco (teclas virtuales)

# --- VISIÓN ---
FINGERS_ID = [8, 12, 16, 20]
CAMERA_INDEX = 0

# --- JUEGO ---
FALL_SPEED = 6
HIT_LINE_Y = IMG_SIZE[1] - 20
HIT_TOLERANCE = 30
# Movemos el botón a una posición cómoda para la ventana de CÁMARA (640x480 aprox)
BUTTON_RECT = (10, 10, 200, 50) # x, y, w, h

# Melodía: Twinkle Twinkle
FPS = 30
BPM = 120
FRAMES_PER_BEAT = int(round((60 / BPM) * FPS))
SPAWN_Y = -40

TWINKLE_MELODY = [
    ("DO", 1), ("DO", 1), ("SOL", 1), ("SOL", 1), ("LA", 1), ("LA", 1), ("SOL", 2),
    ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 1), ("RE", 1), ("DO", 2),
    ("SOL", 1), ("SOL", 1), ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 2),
    ("SOL", 1), ("SOL", 1), ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 2),
    ("DO", 1), ("DO", 1), ("SOL", 1), ("SOL", 1), ("LA", 1), ("LA", 1), ("SOL", 2),
    ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 1), ("RE", 1), ("DO", 2),
]
