import cv2
import numpy as np
import os

import config
from instrument_type import InstrumentType
from colors import *

class PianoKeyboardUI:
    def __init__(self):
        self.key_width = config.IMG_SIZE[0] // 8
        self.black_h = int(config.IMG_SIZE[1] * config.BLACK_NOTE_HEIGHT_RATIO)
        self.black_notes_rects = self._precompute_black_keys()

        self.icons = {}
        self._load_icons()

    def _load_icons(self):
        for inst in InstrumentType:
            filename = f"img/{inst.value.lower()}.png" 
            if os.path.exists(filename):
                img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
                self.icons[inst.value] = cv2.resize(img, (config.INST_ICON_SIZE, config.INST_ICON_SIZE))
            else:
                print(f"Icono {filename} no encontrado.")
                pass

    def _precompute_black_keys(self):
        rects = []
        black_w = int(self.key_width * config.BLACK_NOTE_WIDTH_RATIO)
        for idx, name in config.BLACK_NOTES_MAP:
            cx = (idx + 1) * self.key_width
            x1 = int(cx - black_w // 2)
            x2 = int(cx + black_w // 2)
            rects.append((x1, 0, x2, self.black_h, name))
        return rects

    def draw_piano_window(self, background_img: np.ndarray, active_notes: set, finger_data: dict, game_obj) -> np.ndarray:
        if background_img.shape[:2] != (config.IMG_SIZE[1], config.IMG_SIZE[0]):
            background_img = cv2.resize(background_img, config.IMG_SIZE)

        overlay = background_img.copy()
        self._draw_keys_on_overlay(overlay, active_notes)
        canvas = cv2.addWeighted(overlay, config.TRANSPARENCY_ALPHA, background_img, 1 - config.TRANSPARENCY_ALPHA, 0)

        self._draw_keys_borders_and_text(canvas)

        if game_obj.mode == "GAME":
            self._draw_falling_notes(canvas, game_obj.falling_notes)
            self._draw_score(canvas, game_obj.score)
            
            # HIT LINE
            cv2.line(canvas, 
                     (0, config.HIT_LINE_Y), 
                     (config.IMG_SIZE[0], config.HIT_LINE_Y), 
                     UI_HIT_LINE, 2)

        self._draw_finger_points(canvas, finger_data)
        return canvas

    def draw_camera_overlay(self, frame: np.ndarray, game_mode: str, 
                          current_instrument: str, inst_menu_open: bool,
                          current_melody: str, melody_menu_open: bool):
        
        # Botón de Modo
        self._draw_button(frame, config.BUTTON_RECT, f"MODO: {game_mode}")

        if game_mode == "GAME":
            self._draw_menu(frame, config.MENU_RECT, "Melodia", current_melody, 
                          config.MELODIES.keys(), melody_menu_open)

        elif game_mode == "FREE":
            self._draw_instrument_selector(frame, config.INST_ICON_POS, 
                                         current_instrument, inst_menu_open)

    def _draw_button(self, frame, rect, text):
        x, y, w, h = rect
        sub_img = frame[y:y+h, x:x+w]

        white = np.full(sub_img.shape, UI_BTN_BG_OVERLAY, dtype=np.uint8)
        frame[y:y+h, x:x+w] = cv2.addWeighted(sub_img, 0.5, white, 0.5, 0)

        cv2.rectangle(frame, (x, y), (x+w, y+h), UI_BTN_BORDER, 2)
        cv2.putText(frame, text, (x+10, y+30), 
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, UI_BTN_TEXT, 2)

    def _draw_menu(self, frame, rect, title, current, options, is_open):
        x, y, w, h = rect

        # Cabecera del menú
        cv2.rectangle(frame, (x, y), (x+w, y+h), UI_MENU_HEADER_BG, -1)
        cv2.putText(frame, f"{current}", (x+10, y+35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, UI_MENU_HEADER_TEXT, 2)

        if is_open:
            for i, opt in enumerate(options):
                iy = y + (i+1)*(h+2)
                
                # Fondo y borde de opción
                cv2.rectangle(frame, (x, iy), (x+w, iy+h), UI_MENU_OPT_BG, -1)
                cv2.rectangle(frame, (x, iy), (x+w, iy+h), UI_MENU_OPT_BORDER, 1)
                
                # Texto de opción
                cv2.putText(frame, opt, (x+10, iy+35), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, UI_MENU_OPT_TEXT, 1)

    def _draw_instrument_selector(self, frame, pos, current_inst_str, is_open):
        x, y = pos
        size = config.INST_ICON_SIZE

        # Dibujar Icono Actual
        if current_inst_str in self.icons:
            icon = self.icons[current_inst_str][:,:,:3]
            h_icon, w_icon = icon.shape[:2]
            frame[y:y+h_icon, x:x+w_icon] = icon
        else:
            cv2.rectangle(frame, (x, y), (x+size, y+size), UI_ICON_PLACEHOLDER_BG, -1)

        # Borde del selector cerrado
        cv2.rectangle(frame, (x, y), (x+size, y+size), UI_ICON_BORDER_DEFAULT, 2)

        if is_open:
            for i, inst_enum in enumerate(InstrumentType):
                iy = y + (i+1)*(size+5)
                inst_str = inst_enum.value

                # Dibujar opción
                if inst_str in self.icons:
                    icon = self.icons[inst_str][:,:,:3]
                    frame[iy:iy+size, x:x+size] = icon
                else:
                    cv2.rectangle(frame, (x, iy), (x+size, iy+size), UI_ICON_BG_EMPTY, -1)

                # Bordes
                color = UI_ICON_BORDER_SELECTED if inst_str == current_inst_str else UI_ICON_BORDER_UNSELECTED
                cv2.rectangle(frame, (x, iy), (x+size, iy+size), color, 2)

    def _draw_keys_on_overlay(self, overlay, active_notes):
        # Teclas Blancas
        for i, note in enumerate(config.WHITE_NOTES):
            x1, x2 = i * self.key_width, (i + 1) * self.key_width

            color = UI_KEY_WHITE_ACTIVE if note in active_notes else UI_KEY_WHITE_INACTIVE
            cv2.rectangle(overlay, (x1, 0), (x2, config.IMG_SIZE[1]), color, -1)

        # Teclas Negras
        for x1, y1, x2, y2, name in self.black_notes_rects:
            color = UI_KEY_BLACK_ACTIVE if name in active_notes else UI_KEY_BLACK_INACTIVE
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)

    def _draw_keys_borders_and_text(self, canvas):
        # Blancas
        for i, note in enumerate(config.WHITE_NOTES):
            x1, x2 = i * self.key_width, (i + 1) * self.key_width
            cv2.rectangle(canvas, (x1, 0), (x2, config.IMG_SIZE[1]), UI_KEY_WHITE_BORDER, 2)
            cv2.putText(canvas, note, (x1 + 10, config.IMG_SIZE[1] - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, UI_KEY_WHITE_TEXT, 2) 

        # Negras
        for x1, y1, x2, y2, name in self.black_notes_rects:
            cv2.rectangle(canvas, (x1, y1), (x2, y2), UI_KEY_BLACK_BORDER, 1)

    def _draw_falling_notes(self, canvas, falling_notes):
        for n in falling_notes:
            color = UI_NOTE_HIT if n["hit"] else UI_NOTE_FALLING 
            
            x1 = n["key_idx"] * self.key_width + 10
            x2 = x1 + self.key_width - 20
            y1, y2 = int(n["y"]), int(n["y"] + 30)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, -1)

    def _draw_score(self, canvas, score):
        cv2.putText(canvas, f"SCORE: {score}", (config.IMG_SIZE[0] - 200, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, UI_SCORE_TEXT, 2)

    def _draw_finger_points(self, canvas, finger_data):
        for key, data in finger_data.items():
            px, py = data['pos']
            if 0 <= px < config.IMG_SIZE[0] and 0 <= py < config.IMG_SIZE[1]:
                cv2.circle(canvas, (px, py), 6, UI_FINGER_DOT_FILL, -1)
                cv2.circle(canvas, (px, py), 8, UI_FINGER_DOT_BORDER, 1)

    def get_key_at_point(self, x: int, y: int) -> str | None:
        for x1, y1, x2, y2, name in self.black_notes_rects:
            if x1 < x < x2 and y1 < y < y2:
                return name
        idx = x // self.key_width
        if 0 <= idx < len(config.WHITE_NOTES):
            return config.WHITE_NOTES[idx]
        return None
