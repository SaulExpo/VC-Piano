import pygame
import numpy as np
from typing import Dict, Any

from config import SAMPLE_RATE, FREQUENCIES, ALL_NOTES

class SoundGenerator:
    """Genera las ondas de sonido (arrays de numpy)."""

    @staticmethod
    def generate_piano_wave(frequency: float, duration: float = 2.0) -> np.ndarray:
        """Genera una onda con armónicos tipo piano."""
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        
        # Fundamental + Armónicos
        wave = (
            0.5 * np.sin(2 * np.pi * frequency * t) +
            0.3 * np.sin(2 * np.pi * frequency * 2 * t) +
            0.1 * np.sin(2 * np.pi * frequency * 3 * t)
        )
        
        # Envolvente de ataque rápido (para que no suene 'pop')
        attack = int(SAMPLE_RATE * 0.01)
        wave[:attack] *= np.linspace(0, 1, attack)
        
        # Convertir a 16-bit estéreo
        wave = wave / np.max(np.abs(wave)) # Normalizar
        wave_int = (wave * 32767 * 0.5).astype(np.int16)
        return np.column_stack((wave_int, wave_int))

class AudioEngine:
    sounds: Dict[str, pygame.mixer.Sound] = {}
    active_channels: Dict[str, pygame.mixer.Channel] = {}

    def __init__(self):
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
        pygame.mixer.set_num_channels(32) # Suficientes canales para polifonía
        
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.active_channels: Dict[str, pygame.mixer.Channel] = {}
        
        # Precargar sonidos
        print("Generando sintetizador...")
        for note in ALL_NOTES:
            freq = FREQUENCIES[note]
            wave = SoundGenerator.generate_piano_wave(freq)
            self.sounds[note] = pygame.sndarray.make_sound(wave)

    def note_on(self, note_name: str, velocity: float = 1.0):
        """Inicia la nota. Si ya suena, la reinicia."""
        if note_name not in self.sounds: return
        
        # Si la nota ya está sonando, forzamos el stop anterior (o la dejamos sonar, depende del gusto)
        # Aquí elegimos reiniciar para evitar saturación
        if note_name in self.active_channels and self.active_channels[note_name].get_busy():
            self.active_channels[note_name].stop()

        # Buscar un canal libre
        channel = pygame.mixer.find_channel()
        if channel:
            sound = self.sounds[note_name]
            sound.set_volume(min(1.0, velocity))
            # loops=-1 hace que suene en bucle hasta que llamemos a note_off
            # Ojo: Para piano real, quizás quieras loops=0 y un audio largo, 
            # pero loops=-1 da sustain infinito.
            channel.play(sound, loops=-1) 
            self.active_channels[note_name] = channel

    def note_off(self, note_name: str):
        """Detiene la nota con un fadeout (Release)."""
        if note_name in self.active_channels:
            channel = self.active_channels[note_name]
            # Desvanecer en 300ms (Release)
            channel.fadeout(300) 
            del self.active_channels[note_name]
