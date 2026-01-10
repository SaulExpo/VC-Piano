import config

class RhythmGame:
    def __init__(self):
        self.mode = "FREE" # "FREE" o "GAME"
        self.score = 0
        self.falling_notes = []

        self.current_melody_name = "TWINKLE"
        self.melody_data = config.MELODIES
        self.melody_names = list(config.MELODIES.keys())

        self.game_frame = 0
        self.next_event_idx = 0
        self.melody_events = self._precompute_melody(self.current_melody_name)
        
        self.button_cooldown = 0

    def _precompute_melody(self, melody_name: str) -> list:
        """Precalcula frames de caída para la melodía seleccionada."""
        melody = self.melody_data.get(melody_name, config.TWINKLE)
        events = []
        t_frames = 0
        frames_to_hit = int(round((config.HIT_LINE_Y - config.SPAWN_Y) / config.FALL_SPEED))
        
        for note, beats in melody:
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

    def change_melody(self, melody_name):
        if melody_name in self.melody_data:
            self.current_melody_name = melody_name
            self.reset_game()
            self.melody_events = self._precompute_melody(melody_name)
            print(f"Melodía cambiada a: {melody_name}")

    def toggle_mode(self):
        if self.button_cooldown > 0: return
        self.mode = "GAME" if self.mode == "FREE" else "FREE"
        if self.mode == "GAME":
            self.reset_game()
        else:
            self.falling_notes = []
        self.button_cooldown = 20

    def reset_game(self):
        self.score = 0
        self.game_frame = 0
        self.next_event_idx = 0
        self.falling_notes = []

    def update(self, pressed_keys_this_frame):
        if self.button_cooldown > 0: self.button_cooldown -= 1
        if self.mode != "GAME": return

        self.game_frame += 1

        # Spawn
        while (self.next_event_idx < len(self.melody_events) and 
               self.game_frame >= self.melody_events[self.next_event_idx]["spawn_frame"]):
            ev = self.melody_events[self.next_event_idx]
            self.falling_notes.append({
                "note": ev["note"], "key_idx": ev["key_idx"],
                "y": config.SPAWN_Y, "hit": False
            })
            self.next_event_idx += 1

        # Física y Colisiones
        active_notes = []
        for n in self.falling_notes:
            n["y"] += config.FALL_SPEED
            if not n["hit"]:
                hit_zone = abs(n["y"] - config.HIT_LINE_Y) < config.HIT_TOLERANCE
                if hit_zone and n["note"] in pressed_keys_this_frame:
                    self.score += 1
                    n["hit"] = True
            if n["y"] < config.IMG_SIZE[1]:
                active_notes.append(n)
        self.falling_notes = active_notes
