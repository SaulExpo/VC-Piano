# ui.py
import cv2
import numpy as np

import config

class PianoUI:
    def __init__(self):
        self.key_width = config.IMG_SIZE[0] // 8
        self.black_h = int(config.IMG_SIZE[1] * config.BLACK_NOTE_HEIGHT_RATIO)
        self.black_notes_rects = self._precompute_black_keys()

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
        """
        Dibuja el piano virtual con transparencia sobre la imagen real recortada.
        """
        # Aseguramos que el background tenga el tamaño correcto
        if background_img.shape[:2] != (config.IMG_SIZE[1], config.IMG_SIZE[0]):
            background_img = cv2.resize(background_img, config.IMG_SIZE)

        # 1. Capa de superposición para transparencia
        overlay = background_img.copy()
        
        # Dibujamos las teclas en el overlay (rellenas)
        self._draw_keys_on_overlay(overlay, active_notes)

        # 2. Mezclar overlay con fondo original (Transparencia)
        # alpha * overlay + beta * background + gamma
        canvas = cv2.addWeighted(overlay, config.TRANSPARENCY_ALPHA, background_img, 1 - config.TRANSPARENCY_ALPHA, 0)

        # 3. Dibujar elementos OPACOS (Bordes, Texto, Puntos de dedos, Notas cayendo)
        #    Estos se dibujan sobre el 'canvas' ya mezclado para que se lean bien.
        self._draw_keys_borders_and_text(canvas)
        
        if game_obj.mode == "GAME":
            self._draw_falling_notes(canvas, game_obj.falling_notes)
            self._draw_score(canvas, game_obj.score)
            cv2.line(canvas, (0, config.HIT_LINE_Y), (config.IMG_SIZE[0], config.HIT_LINE_Y), (0,0,255), 2)

        self._draw_finger_points(canvas, finger_data)

        return canvas

    def draw_camera_overlay(self, frame: np.ndarray, game_mode: str):
        """Dibuja el botón y la info en la ventana de la CÁMARA."""
        bx, by, bw, bh = config.BUTTON_RECT
        
        # Fondo botón semitransparente
        sub_img = frame[by:by+bh, bx:bx+bw]
        white_rect = np.full(sub_img.shape, 255, dtype=np.uint8)
        res = cv2.addWeighted(sub_img, 0.5, white_rect, 0.5, 1.0)
        frame[by:by+bh, bx:bx+bw] = res

        # Borde y Texto
        cv2.rectangle(frame, (bx, by), (bx+bw, by+bh), (0, 0, 0), 2)
        
        text = "MODO: PIANO" if game_mode == "FREE" else "MODO: JUEGO"
        # Centrar texto un poco
        cv2.putText(frame, text, (bx+10, by+35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # --- Ayudantes de dibujo ---

    def _draw_keys_on_overlay(self, overlay, active_notes):
        # Solo dibujamos el relleno de colores aquí para la transparencia
        
        # Blancas
        for i, note in enumerate(config.WHITE_NOTES):
            x1, x2 = i * self.key_width, (i + 1) * self.key_width
            if note in active_notes:
                cv2.rectangle(overlay, (x1, 0), (x2, config.IMG_SIZE[1]), (0, 255, 0), -1)
            else:
                # Color gris claro base para que se note que hay tecla virtual
                cv2.rectangle(overlay, (x1, 0), (x2, config.IMG_SIZE[1]), (200, 200, 200), -1)

        # Negras
        for x1, y1, x2, y2, name in self.black_notes_rects:
            if name in active_notes:
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 200, 0), -1)
            else:
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (50, 50, 50), -1)

    def _draw_keys_borders_and_text(self, canvas):
        # Bordes y texto (Opacos)
        for i, note in enumerate(config.WHITE_NOTES):
            x1, x2 = i * self.key_width, (i + 1) * self.key_width
            cv2.rectangle(canvas, (x1, 0), (x2, config.IMG_SIZE[1]), (0, 0, 0), 2)
            cv2.putText(canvas, note, (x1 + 10, config.IMG_SIZE[1] - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 2) # Texto negro fuerte

        for x1, y1, x2, y2, name in self.black_notes_rects:
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (255, 255, 255), 1)

    def _draw_falling_notes(self, canvas, falling_notes):
        for n in falling_notes:
            color = (0, 255, 0) if n["hit"] else (255, 0, 0) 
            x1 = n["key_idx"] * self.key_width + 10
            x2 = x1 + self.key_width - 20
            y1, y2 = int(n["y"]), int(n["y"] + 30)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, -1)

    def _draw_score(self, canvas, score):
        cv2.putText(canvas, f"SCORE: {score}", (config.IMG_SIZE[0] - 200, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    def _draw_finger_points(self, canvas, finger_data):
        for key, data in finger_data.items():
            px, py = data['pos']
            if 0 <= px < config.IMG_SIZE[0] and 0 <= py < config.IMG_SIZE[1]:
                cv2.circle(canvas, (px, py), 6, (0, 0, 255), -1)
                cv2.circle(canvas, (px, py), 8, (255, 255, 255), 1)

    def get_key_at_point(self, x: int, y: int) -> str | None:
        # Misma lógica de detección
        for x1, y1, x2, y2, name in self.black_notes_rects:
            if x1 < x < x2 and y1 < y < y2:
                return name
        idx = x // self.key_width
        if 0 <= idx < len(config.WHITE_NOTES):
            return config.WHITE_NOTES[idx]
        return None
