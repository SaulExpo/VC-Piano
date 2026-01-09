# main.py
import cv2
import numpy as np
import config
import pygame

from vision import HandTracker, calibrate_camera
from audio_engine import AudioEngine
from ui import PianoUI
from game import RhythmGame

mouse_clicked = False
mouse_pos = (0, 0)

# Callback ahora va asociado a la ventana "Camara"
def mouse_callback_camera(event, x, y, flags, param):
    global mouse_clicked, mouse_pos
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True
        mouse_pos = (x, y)

def main():
    global mouse_clicked, mouse_pos
    
    # 1. SETUP
    try:
        src_points = np.load("piano_points.npy")
    except FileNotFoundError:
        src_points = calibrate_camera()
        np.save("piano_points.npy", src_points)

    dst_points = np.array([
        [0, 0], [config.IMG_SIZE[0], 0],
        [config.IMG_SIZE[0], config.IMG_SIZE[1]], [0, config.IMG_SIZE[1]]
    ], dtype=np.float32)
    
    H = cv2.getPerspectiveTransform(src_points, dst_points)

    tracker = HandTracker()
    audio = AudioEngine()
    ui = PianoUI()
    game = RhythmGame()
    
    cap = cv2.VideoCapture(0)

    # Configuramos la ventana de Cámara con el callback
    cv2.namedWindow("Camara")
    cv2.setMouseCallback("Camara", mouse_callback_camera)
    
    cv2.namedWindow("Piano Virtual")

    active_keys_state = set()

    print("--- SISTEMA LISTO ---")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # --- 2. PREPARAR FONDOS ---
        # Creamos la vista "rectificada" del piano real para usarla de fondo
        piano_warped = cv2.warpPerspective(frame, H, config.IMG_SIZE)

        # --- 3. VISION ---
        results, frame_debug = tracker.process(frame)
        finger_data = tracker.get_finger_data(results, frame.shape[1], frame.shape[0], H)
        
        # --- 4. INPUT TECLAS ---
        detected_keys_this_frame = set()
        for key_id, data in finger_data.items():
            px, py = data['pos']
            # Chequeo de límites
            if 0 <= px < config.IMG_SIZE[0] and 0 <= py < config.IMG_SIZE[1]:
                note = ui.get_key_at_point(px, py)
                if note:
                    detected_keys_this_frame.add(note)

        # --- 5. LOGICA INTERFAZ / JUEGO ---
        # Detectar clic en la ventana de CAMARA
        if mouse_clicked:
            mx, my = mouse_pos
            bx, by, bw, bh = config.BUTTON_RECT
            if bx < mx < bx + bw and by < my < by + bh:
                game.toggle_mode()
                print(f"Modo cambiado a: {game.mode}")
            mouse_clicked = False

        game.update(detected_keys_this_frame)

        # --- 6. AUDIO ---
        keys_to_start = detected_keys_this_frame - active_keys_state
        keys_to_stop = active_keys_state - detected_keys_this_frame
        
        for note in keys_to_start:
            audio.note_on(note)
        for note in keys_to_stop:
            audio.note_off(note)
            
        active_keys_state = detected_keys_this_frame

        # --- 7. RENDERIZADO ---
        
        # A. Ventana Piano: Pasamos 'piano_warped' como fondo
        piano_final_img = ui.draw_piano_window(piano_warped, active_keys_state, finger_data, game)
        
        # B. Ventana Cámara: Dibujamos el overlay del botón sobre el frame original
        ui.draw_camera_overlay(frame_debug, game.mode)
        
        cv2.imshow("Camara", frame_debug)
        cv2.imshow("Piano Virtual", piano_final_img)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()

if __name__ == "__main__":
    main()
