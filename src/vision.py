import cv2
import mediapipe as mp
import numpy as np

from config import FINGERS_ID

class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=2, 
            min_detection_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Estado para cálculos de velocidad
        self.prev_fy = {} 
        self.fz_smooth = {}

    def process(self, frame: np.ndarray) -> tuple:
        """Retorna los landmarks crudos y la imagen con dibujo."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_lm, self.mp_hands.HAND_CONNECTIONS)
        return results, frame

    def get_finger_data(self, results, width: int, height: int, H: np.ndarray) -> dict:
        """
        Calcula posición proyectada y velocidad de cada dedo.
        Retorna: { (hand_id, finger_id): {'pos': (x, y), 'velocity': v, 'z': z} }
        """
        data = {}
        if not results.multi_hand_landmarks:
            return data

        for h_id, hand_lm in enumerate(results.multi_hand_landmarks):
            for f_id in FINGERS_ID:
                lm = hand_lm.landmark[f_id]
                
                # Coordenadas pantalla
                cx, cy = int(lm.x * width), int(lm.y * height)
                
                # Proyección Homográfica
                pt_original = np.array([[[cx, cy]]], dtype=np.float32)
                pt_flat = cv2.perspectiveTransform(pt_original, H)
                px, py = int(pt_flat[0][0][0]), int(pt_flat[0][0][1])
                
                # Cálculo de velocidad (eje Y original)
                key = (h_id, f_id)
                prev = self.prev_fy.get(key, cy)
                velocity = cy - prev
                self.prev_fy[key] = cy
                
                data[key] = {
                    'pos': (px, py),
                    'velocity': velocity,
                    'raw_pos': (cx, cy)
                }
        return data

def calibrate_camera():
    """Función bloqueante para obtener la homografía al inicio."""
    points = []
    
    def click_event(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append([x, y])
            print(f"Punto {len(points)}: {x, y}")

    cap = cv2.VideoCapture(0)
    print("--- CALIBRACION ---")
    print("Haz click en las 4 esquinas del piano imaginario en orden (TL, TR, BR, BL)")
    
    while True:
        ret, frame = cap.read()
        if not ret: continue
        
        for p in points:
            cv2.circle(frame, tuple(p), 5, (0, 255, 0), -1)
            
        cv2.imshow("Calibracion", frame)
        cv2.setMouseCallback("Calibracion", click_event)
        
        if cv2.waitKey(1) & 0xFF == 27 or len(points) == 4:
            break
            
    cap.release()
    cv2.destroyAllWindows()
    
    if len(points) < 4:
        raise Exception("No se calibraron los 4 puntos")
        
    return np.array(points, dtype=np.float32)
