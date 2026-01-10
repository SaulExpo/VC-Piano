import numpy as np

from config import SAMPLE_RATE
from instrument_type import Instrument


class PianoInstrument(Instrument):
    @property
    def release_time_ms(self) -> int:
        return 400 

    @property
    def loops(self) -> int:
        return -1 

    def generate_wave(self, freq: float) -> np.ndarray:
        duration = 3.0 
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)

        wave = (
            0.5 * np.sin(2 * np.pi * freq * t) +
            0.3 * np.sin(2 * np.pi * freq * 2 * t) +
            0.1 * np.sin(2 * np.pi * freq * 3 * t)
        )

        attack_len = int(SAMPLE_RATE * 0.02)
        if attack_len < len(wave):
            wave[:attack_len] *= np.linspace(0, 1, attack_len)

        return self._normalize(wave, volume=0.8)


class OrganInstrument(Instrument):
    @property
    def release_time_ms(self) -> int:
        return 150

    @property
    def loops(self) -> int:
        return -1 

    def generate_wave(self, freq: float) -> np.ndarray:
        duration = 2.0
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)

        attack = 0.05
        env = np.ones_like(t)
        env[t < attack] = t[t < attack] / attack

        wave = (1.0 * np.sin(2 * np.pi * freq * t) + 
                0.5 * np.sin(2 * np.pi * freq * 2 * t) +
                0.3 * np.sin(2 * np.pi * freq * 4 * t))
        wave *= env
        
        return self._normalize(wave, volume=0.5)


class SynthInstrument(Instrument):
    @property
    def release_time_ms(self) -> int:
        return 200

    @property
    def loops(self) -> int:
        return -1

    def generate_wave(self, freq: float) -> np.ndarray:
        duration = 2.0
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        
        attack = 0.02
        env = np.ones_like(t) 
        env[t < attack] = t[t < attack] / attack
        
        saw = 2 * (t * freq - np.floor(0.5 + t * freq))
        square = np.sign(np.sin(2 * np.pi * freq * t))
        wave = (0.7 * saw + 0.3 * square) * env
        
        return self._normalize(wave, volume=0.4)


class ViolinInstrument(Instrument):
    @property
    def release_time_ms(self) -> int:
        return 300

    @property
    def loops(self) -> int:
        return -1

    def generate_wave(self, freq: float) -> np.ndarray:
        duration = 3.0 
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        
        attack = 0.15
        env = np.ones_like(t)
        env[t < attack] = t[t < attack] / attack
        
        vibrato = 1 + 0.002 * np.sin(2 * np.pi * 6.0 * t)
        f = freq * vibrato
        
        wave = (1.0 * np.sin(2 * np.pi * f * t) + 
                0.8 * np.sin(2 * np.pi * f * 2 * t) +
                0.4 * np.sin(2 * np.pi * f * 3 * t)) * env
        
        return self._normalize(wave, volume=0.5)


class TrumpetInstrument(Instrument):
    @property
    def release_time_ms(self) -> int:
        return 150

    @property
    def loops(self) -> int:
        return -1

    def generate_wave(self, freq: float) -> np.ndarray:
        duration = 2.0
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        
        attack = 0.05
        env = np.ones_like(t)
        env[t < attack] = t[t < attack] / attack
        
        wave = (1.0 * np.sin(2 * np.pi * freq * t) + 
                0.8 * np.sin(2 * np.pi * freq * 3 * t) +
                0.5 * np.sin(2 * np.pi * freq * 5 * t)) * env
                
        return self._normalize(wave, volume=0.5)
