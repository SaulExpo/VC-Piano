# %%

import pygame
import cv2
import numpy as np
import mediapipe as mp

# %% [markdown]
# Obtener puntos para la homografía

# %%

points = []

def get_points(event, x, y, flags, param):
    global points
    img = param["img"]

    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        cv2.circle(img, (x, y), 6, (0, 255, 0), -1)
        cv2.imshow("Calibracion", img)
        print(points)

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

clone = frame.copy()
cv2.imshow("Calibracion", clone)
cv2.setMouseCallback("Calibracion", get_points, {"img": clone})
cv2.waitKey(0)
cv2.destroyAllWindows()

points = np.array(points, dtype=np.float32)

np.save("piano_points.npy", points)
print("Puntos guardados:", points)

# %% [markdown]
# Obtener Sonidos (Ayuda total chatgpt no me entero de sonidos)

# %%

SAMPLE_RATE = 44100 # 44Khz

def envelope_adsr(t, duration):
    """
    Envolvente aproximada tipo piano:
    - Ataque muy rápido
    - Decaimiento corto
    - Sustain medio
    - Release al final
    """
    attack = 0.01       # 10 ms
    decay = 0.08        # 80 ms
    sustain = 0.6
    release = 0.3       # 300 ms

    env = np.zeros_like(t)

    # Attack
    idx = t < attack
    env[idx] = (t[idx] / attack)

    # Decay
    idx = (t >= attack) & (t < attack + decay)
    env[idx] = 1 - (1 - sustain) * ((t[idx] - attack) / decay)

    # Sustain
    idx = (t >= attack + decay) & (t < duration - release)
    env[idx] = sustain

    # Release
    idx = t >= (duration - release)
    if np.any(idx):
        env[idx] = sustain * (1 - (t[idx] - (duration - release)) / release)
        env[env < 0] = 0.0

    return env


def generate_piano_tone(frequency, duration=0.8, volume=0.5, sample_rate=SAMPLE_RATE):
    """
    Genera una nota tipo piano:
    - Fundamental ligeramente desafinada en 2 cuerdas (detune)
    - Armónicos extra
    - Envolvente ADSR tipo piano
    - Resonancia simple de caja
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Envolvente
    env = envelope_adsr(t, duration)

    # Detune pequeño (2 cuerdas por nota)
    f1 = frequency * 0.997
    f2 = frequency * 1.003
    base = 0.5 * (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t))

    # Armónicos (sobre la fundamental "ideal")
    wave = (
        1.0 * base +
        0.6 * np.sin(2 * np.pi * frequency * 2 * t) +
        0.3 * np.sin(2 * np.pi * frequency * 3 * t) +
        0.15 * np.sin(2 * np.pi * frequency * 4 * t) +
        0.10 * np.sin(2 * np.pi * frequency * 5 * t)
    )

    # Aplicar envolvente
    wave *= env

    # Resonancia simple (filtro IIR muy básico)
    r = 0.4
    y = np.zeros_like(wave)
    for i in range(len(wave)):
        if i == 0:
            y[i] = wave[i]
        else:
            y[i] = wave[i] + r * y[i - 1]

    # Normalizar
    max_val = np.max(np.abs(y))
    if max_val > 0:
        y = y / max_val

    y = (y * 32767 * volume).astype(np.int16)
    return y

# %% [markdown]
# Inicializar Sonido

# %%

frequencies = {
    "DO": 261.63, "DO#": 277.18,
    "RE": 293.66, "RE#": 311.13,
    "MI": 329.63,
    "FA": 349.23, "FA#": 369.99,
    "SOL": 392.00, "SOL#": 415.30,
    "LA": 440.00, "LA#": 466.16,
    "SI": 493.88,
    "DO2": 523.25
}

pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)

ALL_NOTES = ["DO","DO#","RE","RE#","MI","FA","FA#","SOL","SOL#","LA","LA#","SI","DO2"]

note_sounds = {}
for note in ALL_NOTES:
    wave = generate_piano_tone(frequencies[note], duration=0.8, volume=0.7)
    wave_stereo = np.column_stack((wave, wave))
    note_sounds[note] = pygame.sndarray.make_sound(wave_stereo)

# %% [markdown]
# Teclas Blancas y Negras y tamaño de las negras

# %%

WHITE_NOTES = ["DO", "RE", "MI", "FA", "SOL", "LA", "SI", "DO2"]
BLACK_NOTES = [
    (0, "DO#"),
    (1, "RE#"),
    (3, "FA#"),
    (4, "SOL#"),
    (5, "LA#")
]

BLACK_NOTE_WIDTH_RATIO = 0.6
BLACK_NOTE_HEIGHT_RATIO = 0.5

# %% [markdown]
# Configuración MediaPipe

# %%

FINGERS = [8, 12, 16, 20] # Lista de dedos sin pulgar

prev_fy = {} # Valor previo de la coordenada y de cada dedo
finger_was_down = {} # Estado previo de cada dedo (presionado o no)
fz_smooth = {} # Valor suavizado de la coordenada z de cada dedo
finger_velocity = {} # Velocidad vertical de cada dedo

# Inicializar MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

# %% [markdown]
# Inicializar homografía y cámara

# %%

img_size = (800, 300)

src_pts = np.load("piano_points.npy") #Puntos de la homografía

# Obtener las 4 esquinas del dibujo del piano
dst_pts = np.array([
    [0, 0],
    [img_size[0], 0],
    [img_size[0], img_size[1]],
    [0, img_size[1]]
], dtype=np.float32)

H = cv2.getPerspectiveTransform(src_pts, dst_pts)

cap = cv2.VideoCapture(0, cv2.CAP_ANY)

# %% [markdown]
# Detectar Click del ratón

# %%

def mouse_callback(event, x, y, flags, param):
    global mouse_clicked, mouse_x, mouse_y

    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True
        mouse_x, mouse_y = x, y

# %% [markdown]
# Parámetros del juego (Melodía generada automáticamente ChatGPT le damos las gracias :) )

# %%

# Cración del botón y modo determinado (el free es el modo libre del piano y luego cambio a game que es el de las notas)
button_rect = (10, 10, 200, 60)
game_mode = "FREE"
button_cooldown = 0

mouse_clicked = False
mouse_x, mouse_y = 0, 0
falling_notes = []
spawn_timer = 0

SPAWN_INTERVAL = 30   # frames entre notas
FALL_SPEED = 6        # velocidad de caída
HIT_LINE_Y = img_size[1] - 20
score = 0
HIT_TOLERANCE = 25   # margen de error vertical

cv2.namedWindow("Vista Camara")
cv2.setMouseCallback("Vista Camara", mouse_callback)

# ==============================
# MELODÍA: "Twinkle Twinkle" (Do mayor)
# ==============================

FPS = 30
BPM = 120
FRAMES_PER_BEAT = int(round((60 / BPM) * FPS))  # 120 BPM -> 15 frames por beat

SPAWN_Y = -40       # Spawning por encima de la pantalla

# Notas en solfeo (Do= C)
# Twinkle Twinkle Little Star (versión simple en C mayor)
# Duraciones en beats: 1 = negra, 2 = blanca
TWINKLE = [
    ("DO", 1), ("DO", 1), ("SOL", 1), ("SOL", 1), ("LA", 1), ("LA", 1), ("SOL", 2),
    ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 1), ("RE", 1), ("DO", 2),

    ("SOL", 1), ("SOL", 1), ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 2),
    ("SOL", 1), ("SOL", 1), ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 2),

    ("DO", 1), ("DO", 1), ("SOL", 1), ("SOL", 1), ("LA", 1), ("LA", 1), ("SOL", 2),
    ("FA", 1), ("FA", 1), ("MI", 1), ("MI", 1), ("RE", 1), ("RE", 1), ("DO", 2),
]

# Solo usamos teclas blancas para el modo juego (como tu random actual)
# (DO, RE, MI, FA, SOL, LA, SI, DO2)
MELODY_EVENTS = []
t_frames = 0

# Cuántos frames tarda una nota en caer desde SPAWN_Y hasta HIT_LINE_Y
FRAMES_TO_HIT = int(round((HIT_LINE_Y - SPAWN_Y) / FALL_SPEED))

for note, beats in TWINKLE:
    if note not in WHITE_NOTES:
        # si alguna nota no estuviera en blancas, la saltamos (en twinkle no pasa)
        t_frames += beats * FRAMES_PER_BEAT
        continue

    hit_frame = t_frames
    spawn_frame = hit_frame - FRAMES_TO_HIT
    key_index = WHITE_NOTES.index(note)

    MELODY_EVENTS.append({
        "note": note,
        "key": key_index,
        "hit_frame": hit_frame,
        "spawn_frame": spawn_frame
    })

    t_frames += beats * FRAMES_PER_BEAT

# Estado de reproducción de melodía
game_frame = 0
next_event_idx = 0

# %% [markdown]
# Obtener Frames

# %%

def get_frames(cap, H, img_size):
    ret, frame = cap.read()
    if not ret:
        return None, None

    piano_flat = cv2.warpPerspective(frame, H, img_size)
    return frame, piano_flat

# %% [markdown]
# Procesar Manos

# %%

def process_hands(frame, hands, H, FINGERS, fz_smooth, prev_fy,
                  finger_was_down, finger_velocity):
    h_img, w_img, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    finger_points = {} # Coordenadas 2D proyectadas de los dedos
    finger_z = {} # Coordenadas z suavizadas de los dedos

    if result.multi_hand_landmarks:
        for hand_id, hand_landmarks in enumerate(result.multi_hand_landmarks): # Para cada mano detectada

            # Dibujar las conexiones de la mano
            mp_draw.draw_landmarks(
                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
            )

            for f_id in FINGERS: # Para cada dedo
                # Obtener coordenadas del dedo
                lm = hand_landmarks.landmark[f_id]
                fx, fy = int(lm.x * w_img), int(lm.y * h_img)
                fz = lm.z
                key = (hand_id, f_id)

                # Inicializar estructuras si es la primera vez que vemos este dedo
                fz_smooth.setdefault(key, fz)
                prev_fy.setdefault(key, None)
                finger_was_down.setdefault(key, False)
                finger_velocity.setdefault(key, 0)

                #Suavizar coordenada z para evitar ruidos (0.7 y 0.3 son factores de suavizado que puse probando)
                fz_smooth[key] = 0.7 * fz_smooth[key] + 0.3 * fz
                finger_z[key] = fz_smooth[key]

                #Dibujar punto en el dedo
                cv2.circle(frame, (fx, fy), 8, (0, 255, 255), -1)

                # Proyectar punto con homografía
                p = np.array([[[fx, fy]]], dtype=np.float32)
                p_flat = cv2.perspectiveTransform(p, H)
                finger_points[key] = (int(p_flat[0][0][0]), int(p_flat[0][0][1]))

    return finger_points, finger_z

# %% [markdown]
# Dibujar Piano

# %%

def draw_piano(piano_flat, img_size, WHITE_NOTES, BLACK_NOTES,
               BLACK_NOTE_WIDTH_RATIO, BLACK_NOTE_HEIGHT_RATIO):

    key_width = img_size[0] // 8 # Ancho de cada tecla blanca
    black_notes_rects = [] # Lista de teclas negras

    # Blancas
    for i in range(8):
        x1, x2 = i * key_width, (i + 1) * key_width # Coordenadas x de la tecla
        cv2.rectangle(piano_flat, (x1, 0), (x2, img_size[1]), (255, 0, 0), 2)
        cv2.putText(piano_flat, WHITE_NOTES[i],
                    (x1 + 20, img_size[1] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Negras
    black_w = int(key_width * BLACK_NOTE_WIDTH_RATIO) # Ancho de tecla negra
    black_h = int(img_size[1] * BLACK_NOTE_HEIGHT_RATIO) # Altura de tecla negra

    for idx, name in BLACK_NOTES: #Para cada tecla negra
        cx = (idx + 1) * key_width # Centro x de la tecla negra
        x1, x2 = int(cx - black_w // 2), int(cx + black_w // 2) # Coordenadas x de la tecla
        y1, y2 = 0, black_h # Altura de la tecla

        black_notes_rects.append((x1, y1, x2, y2, name))

        cv2.rectangle(piano_flat, (x1, y1), (x2, y2), (0, 0, 0), 2)
        cv2.putText(piano_flat, name,
                    (x1 + 5, int(black_h * 0.8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return black_notes_rects, black_h

# %% [markdown]
# Generar notas por melodía

# %%

def spawn_melody_notes(game_mode, game_frame, MELODY_EVENTS,
                       next_event_idx, falling_notes, SPAWN_Y):

    if game_mode != "GAME":
        return game_frame, next_event_idx

    game_frame += 1

    while next_event_idx < len(MELODY_EVENTS) and \
          game_frame >= MELODY_EVENTS[next_event_idx]["spawn_frame"]:

        ev = MELODY_EVENTS[next_event_idx]
        falling_notes.append({
            "note": ev["note"],
            "key": ev["key"],
            "y": SPAWN_Y
        })
        next_event_idx += 1

    return game_frame, next_event_idx

# %% [markdown]
# Botón del cambio de modo

# %%

def handle_mode_button(frame, button_rect, mouse_clicked, mouse_x, mouse_y,
                       button_cooldown, game_mode):

    bx, by, bw, bh = button_rect

    cv2.rectangle(frame, (bx, by), (bx+bw, by+bh), (50,50,50), -1)
    cv2.rectangle(frame, (bx, by), (bx+bw, by+bh), (255,255,255), 2)

    text = "MODO: PIANO" if game_mode == "FREE" else "MODO: JUEGO"
    cv2.putText(frame, text, (bx+10, by+40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    if button_cooldown > 0:
        button_cooldown -= 1

    mode_changed = False

    if mouse_clicked and button_cooldown == 0:
        if bx < mouse_x < bx + bw and by < mouse_y < by + bh:
            game_mode = "GAME" if game_mode == "FREE" else "FREE"
            button_cooldown = 20
            mode_changed = True

    return game_mode, button_cooldown, mode_changed

# %% [markdown]
# Actualizar y dibujar notas

# %%

def update_and_draw_notes(piano_flat, falling_notes, FALL_SPEED,
                          img_size, HIT_LINE_Y):

    new_notes = []
    key_width = img_size[0] // 8

    for n in falling_notes:
        n["y"] += FALL_SPEED

        x1 = n["key"] * key_width + 10
        x2 = x1 + key_width - 20
        y1, y2 = int(n["y"]), int(n["y"] + 30)

        cv2.rectangle(piano_flat, (x1, y1), (x2, y2), (0,255,0), -1)

        if n["y"] < img_size[1]:
            new_notes.append(n)

    cv2.line(piano_flat, (0, HIT_LINE_Y),
             (img_size[0], HIT_LINE_Y), (0,0,255), 2)

    return new_notes

# %% [markdown]
# Detectar teclas

# %%

def detect_pressed_keys(finger_points, prev_fy,
                         finger_was_down,
                         finger_velocity, black_notes_rects,
                         black_h, img_size, WHITE_NOTES):

    pressed_keys = set()
    key_width = img_size[0] // 8

    for key, (fx_p, fy_p) in finger_points.items():

        prev_y = prev_fy[key] # Coordenada y previa del dedo
        velocity = 0 if prev_y is None else fy_p - prev_y # Velocidad vertical
        finger_velocity[key] = velocity # Actualizar velocidad

        finger_is_down = False
        PRESS_DELTA = 6 # Definir delta para considerar presionado

        if prev_y is not None:
            if velocity > 0.3 and (fy_p - prev_y) > PRESS_DELTA: # Si la velocidad y el desplazamiento superan el umbral
                finger_is_down = True # Marcar dedo como presionado

        prev_fy[key] = fy_p

        # ---------- DETECCIÓN DE TECLA ----------
        if finger_is_down and not finger_was_down[key]:
            pressed_note = None

            for x1, y1, x2, y2, name in black_notes_rects: # Comprobar teclas negras primero
                if x1 < fx_p < x2 and fy_p < black_h * 1.2: # Si el dedo está sobre una tecla negra
                    pressed_note = name
                    break

            if pressed_note is None:
                for i in range(8):
                    if i * key_width < fx_p < (i + 1) * key_width and fy_p >= black_h * 1.2: # Tecla blanca
                        pressed_note = WHITE_NOTES[i]
                        break

            if pressed_note:
                pressed_keys.add((*key, pressed_note))

        finger_was_down[key] = finger_is_down

    return pressed_keys

# %% [markdown]
# Bucle Principal

# %%

while True:
    frame, piano_flat = get_frames(cap, H, img_size)
    if frame is None:
        break

    finger_points, finger_z = process_hands(
        frame, hands, H, FINGERS,
        fz_smooth, prev_fy,
        finger_was_down, finger_velocity
    )

    black_notes_rects, black_h = draw_piano(
        piano_flat, img_size,
        WHITE_NOTES, BLACK_NOTES,
        BLACK_NOTE_WIDTH_RATIO, BLACK_NOTE_HEIGHT_RATIO
    )

    game_mode, button_cooldown, mode_changed = handle_mode_button(
        frame, button_rect, mouse_clicked,
        mouse_x, mouse_y,
        button_cooldown, game_mode
    )
    mouse_clicked = False

    if mode_changed and game_mode == "GAME":
        falling_notes = []
        score = 0
        game_frame = 0
        next_event_idx = 0

    game_frame, next_event_idx = spawn_melody_notes(
        game_mode, game_frame,
        MELODY_EVENTS, next_event_idx,
        falling_notes, SPAWN_Y
    )

    if game_mode == "GAME":
        falling_notes = update_and_draw_notes(
            piano_flat, falling_notes,
            FALL_SPEED, img_size, HIT_LINE_Y
        )

    pressed_keys = detect_pressed_keys(
        finger_points, prev_fy, finger_was_down,
        finger_velocity, black_notes_rects,
        black_h, img_size, WHITE_NOTES
    )

    # ---------- REPRODUCIR NOTAS ----------
    if game_mode == "FREE":
        for hand_id, f_id, key in pressed_keys:
            vel = max(0, min(finger_velocity[(hand_id, f_id)], 20))
            vol = 0.2 + 0.8 * (vel / 20)

            note_sounds[key].set_volume(vol)
            note_sounds[key].play()


    # ---------- LOGICA DE JUEGO ----------
    if game_mode == "GAME":
        new_falling_notes = []

        for n in falling_notes:
            hit = False

            for (_, _, pressed_note) in pressed_keys:
                if (
                    pressed_note == n["note"] and
                    abs(n["y"] - HIT_LINE_Y) < HIT_TOLERANCE
                ):
                    note_sounds[pressed_note].play()
                    score += 1
                    hit = True
                    break

            if not hit:
                new_falling_notes.append(n)

        falling_notes = new_falling_notes

    cv2.putText(
        frame,
        f"SCORE: {score}",
        (20, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Vista Camara", frame)
    cv2.imshow("Piano Plano", piano_flat)
    if cv2.waitKey(1) & 0xFF == 27:
            break


cap.release()
cv2.destroyAllWindows()
pygame.quit()
