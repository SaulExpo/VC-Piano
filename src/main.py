import cv2
import numpy as np
import pygame

import config
from vision import HandTracker, calibrate_camera
from audio_engine import AudioEngine
from ui import PianoKeyboardUI
from game import RhythmGame
from instrument_type import InstrumentType

mouse_clicked = False
mouse_pos = (0, 0)
inst_menu_open = False
melody_menu_open = False

def mouse_callback_camera(event, x, y, flags, param):
    global mouse_clicked, mouse_pos
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True
        mouse_pos = (x, y)

def check_ui_clicks(game, audio: AudioEngine):
    global mouse_clicked, inst_menu_open, melody_menu_open
    
    if not mouse_clicked: return
    mx, my = mouse_pos
    
    # Botón de Modo
    bx, by, bw, bh = config.BUTTON_RECT
    if bx < mx < bx + bw and by < my < by + bh:
        game.toggle_mode()
        print(f"Modo cambiado a: {game.mode}")
        mouse_clicked = False
        return

    if game.mode == "GAME":
        mx0, my0, mw, mh = config.MENU_RECT
        if mx0 < mx < mx0 + mw and my0 < my < my0 + mh:
            melody_menu_open = not melody_menu_open
            mouse_clicked = False
            return
        
        if melody_menu_open:
            for i, name in enumerate(config.MELODIES.keys()):
                iy = my0 + (i+1)*(mh+2)
                if mx0 < mx < mx0 + mw and iy < my < iy + mh:
                    game.change_melody(name)
                    melody_menu_open = False
                    mouse_clicked = False
                    return

    elif game.mode == "FREE":
        ix, iy = config.INST_ICON_POS
        isize = config.INST_ICON_SIZE
        # Click en icono actual
        if ix < mx < ix + isize and iy < my < iy + isize:
            inst_menu_open = not inst_menu_open
            mouse_clicked = False
            return
            
        # Click en opciones desplegadas
        if inst_menu_open:
            for i, inst_enum in enumerate(InstrumentType):
                iiy = iy + (i+1)*(isize+5)
                if ix < mx < ix + isize and iiy < my < iiy + isize:
                    audio.set_instrument(inst_enum)
                    inst_menu_open = False
                    mouse_clicked = False
                    return

    mouse_clicked = False

def main():
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
    ui = PianoKeyboardUI()
    game = RhythmGame()
    
    cap = cv2.VideoCapture(config.CAMERA_INDEX)

    cv2.namedWindow("Camara")
    cv2.setMouseCallback("Camara", mouse_callback_camera)
    cv2.namedWindow("Teclado Virtual")

    active_keys_state = set()

    print("--- SISTEMA LISTO ---")

    while True:
        ret, frame = cap.read()
        if not ret: break

        piano_warped = cv2.warpPerspective(frame, H, config.IMG_SIZE)

        results, frame_debug = tracker.process(frame)
        finger_data = tracker.get_finger_data(results, frame.shape[1], frame.shape[0], H)
        
        detected_keys_this_frame = set()
        for key_id, data in finger_data.items():
            px, py = data['pos']
            if 0 <= px < config.IMG_SIZE[0] and 0 <= py < config.IMG_SIZE[1]:
                note = ui.get_key_at_point(px, py)
                if note:
                    detected_keys_this_frame.add(note)

        check_ui_clicks(game, audio)
        game.update(detected_keys_this_frame)

        keys_to_start = detected_keys_this_frame - active_keys_state
        keys_to_stop = active_keys_state - detected_keys_this_frame
        
        for note in keys_to_start:
            audio.note_on(note)
        for note in keys_to_stop:
            audio.note_off(note)
            
        active_keys_state = detected_keys_this_frame

        keyboard_final_img = ui.draw_piano_window(piano_warped, active_keys_state, finger_data, game)
        
        ui.draw_camera_overlay(
            frame_debug, game.mode, 
            audio.current_instrument_type.value, inst_menu_open,
            game.current_melody_name, melody_menu_open
        )

        cv2.imshow("Camara", frame_debug)
        cv2.imshow("Teclado Virtual", keyboard_final_img)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()

if __name__ == "__main__":
    main()
