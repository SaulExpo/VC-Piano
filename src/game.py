import config

class RhythmGame:
    def __init__(self):
        self.mode = "FREE" # "FREE" o "GAME"
        self.score = 0
        self.falling_notes = [] # Lista de dicts: {'note', 'key_idx', 'y'}
        
        # Estado de la melodía
        self.game_frame = 0
        self.next_event_idx = 0
        self.melody_events = self._precompute_melody()
        
        # Cooldown del botón para no cambiar 100 veces por segundo
        self.button_cooldown = 0

    def _precompute_melody(self):
        """Convierte la lista de notas en eventos temporales (frames)."""
        events = []
        t_frames = 0
        frames_to_hit = int(round((config.HIT_LINE_Y - config.SPAWN_Y) / config.FALL_SPEED))
        
        for note, beats in config.TWINKLE_MELODY:
            if note in config.WHITE_NOTES:
                hit_frame = t_frames
                spawn_frame = hit_frame - frames_to_hit
                key_index = config.WHITE_NOTES.index(note)
                
                events.append({
                    "note": note,
                    "key_idx": key_index,
                    "hit_frame": hit_frame,
                    "spawn_frame": spawn_frame
                })
            t_frames += beats * config.FRAMES_PER_BEAT
        return events

    def toggle_mode(self):
        """Cambia entre modo libre y modo juego."""
        if self.button_cooldown > 0: return
        
        if self.mode == "FREE":
            self.mode = "GAME"
            self.reset_game()
        else:
            self.mode = "FREE"
            self.falling_notes = []
            
        self.button_cooldown = 20 # frames de espera

    def reset_game(self):
        self.score = 0
        self.game_frame = 0
        self.next_event_idx = 0
        self.falling_notes = []

    def update(self, pressed_keys_this_frame):
        """Avanza un frame en la lógica del juego."""
        if self.button_cooldown > 0:
            self.button_cooldown -= 1

        if self.mode != "GAME":
            return

        self.game_frame += 1

        # 1. Spawnear nuevas notas
        while (self.next_event_idx < len(self.melody_events) and 
               self.game_frame >= self.melody_events[self.next_event_idx]["spawn_frame"]):
            
            ev = self.melody_events[self.next_event_idx]
            self.falling_notes.append({
                "note": ev["note"],
                "key_idx": ev["key_idx"],
                "y": config.SPAWN_Y,
                "hit": False # Para no contarla doble
            })
            self.next_event_idx += 1

        # 2. Mover notas y limpiar
        active_notes = []
        for n in self.falling_notes:
            n["y"] += config.FALL_SPEED
            
            # Chequear colisión con teclas pulsadas (Solo si no ha sido golpeada ya)
            if not n["hit"]:
                hit_zone = abs(n["y"] - config.HIT_LINE_Y) < config.HIT_TOLERANCE
                if hit_zone and n["note"] in pressed_keys_this_frame:
                    self.score += 1
                    n["hit"] = True # Marcada como golpeada
            
            # Si no ha salido de la pantalla, la mantenemos
            if n["y"] < config.IMG_SIZE[1]:
                active_notes.append(n)
        
        self.falling_notes = active_notes
