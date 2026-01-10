from abc import ABC, abstractmethod
from enum import Enum
import numpy as np


class InstrumentType(Enum):
    PIANO = "PIANO"
    ORGAN = "ORGAN"
    SYNTH = "SYNTH"
    TRUMPET = "TRUMPET"
    VIOLIN = "VIOLIN"

class Instrument(ABC):
    @abstractmethod
    def generate_wave(self, freq: float) -> np.ndarray:
        """Genera el array de numpy con el sonido."""
        pass

    @property
    @abstractmethod
    def release_time_ms(self) -> int:
        """Tiempo de desvanecimiento en milisegundos al soltar la tecla."""
        pass

    @property
    @abstractmethod
    def loops(self) -> int:
        """-1 para bucle infinito (sustain), 0 para reproducción única (piano)."""
        pass

    def _normalize(self, wave, volume=1.0):
        max_val = np.max(np.abs(wave))
        if max_val > 0:
            wave = wave / max_val
        return (wave * 32767 * volume).astype(np.int16)
