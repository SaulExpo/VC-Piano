import pygame
import numpy as np
from typing import Dict

from config import SAMPLE_RATE, FREQUENCIES, ALL_NOTES
from instrument_type import Instrument, InstrumentType
from instruments import OrganInstrument, PianoInstrument, SynthInstrument, TrumpetInstrument, ViolinInstrument

class AudioEngine:
    def __init__(self):
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
        pygame.mixer.set_num_channels(32)

        self.sound_banks: Dict[InstrumentType, Dict[str, pygame.mixer.Sound]] = {}
        self.active_channels: Dict[str, pygame.mixer.Channel] = {}

        self.strategies: Dict[InstrumentType, Instrument] = {
            InstrumentType.PIANO: PianoInstrument(),
            InstrumentType.ORGAN: OrganInstrument(),
            InstrumentType.SYNTH: SynthInstrument(),
            InstrumentType.VIOLIN: ViolinInstrument(),
            InstrumentType.TRUMPET: TrumpetInstrument()
        }

        self.current_instrument_type = InstrumentType.PIANO
        self._preload_sounds()

    def _preload_sounds(self):
        print("Generando instrumentos...")

        for inst_type, strategy in self.strategies.items():
            print(f"  - Sintetizando {inst_type.value}...")
            self.sound_banks[inst_type] = {}
            
            for note in ALL_NOTES:
                freq = FREQUENCIES[note]
                wave = strategy.generate_wave(freq)
                wave_stereo = np.column_stack((wave, wave))
                self.sound_banks[inst_type][note] = pygame.sndarray.make_sound(wave_stereo)
        
        print("Síntesis completada.")

    def set_instrument(self, inst_enum: InstrumentType):
        try:
            self.current_instrument_type = inst_enum
            print(f"Instrumento cambiado a: {inst_enum.value}")
        except ValueError:
            print(f"Error: Instrumento {str(inst_enum)} no existe.")

    @property
    def current_strategy(self) -> Instrument:
        return self.strategies[self.current_instrument_type]

    def note_on(self, note_name: str, velocity: float = 1.0):
        if note_name not in self.sound_banks[self.current_instrument_type]: return

        # Reiniciar nota si ya suena
        if note_name in self.active_channels and self.active_channels[note_name].get_busy():
            self.active_channels[note_name].stop()

        channel = pygame.mixer.find_channel()
        if channel:
            sound = self.sound_banks[self.current_instrument_type][note_name]
            sound.set_volume(min(1.0, velocity))

            loops = self.current_strategy.loops
            channel.play(sound, loops=loops)

            self.active_channels[note_name] = channel

    def note_off(self, note_name: str):
        if note_name in self.active_channels:
            channel = self.active_channels[note_name]

            fade_ms = self.current_strategy.release_time_ms
            channel.fadeout(fade_ms)

            del self.active_channels[note_name]
