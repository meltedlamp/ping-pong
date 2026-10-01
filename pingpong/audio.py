"""Short synthesized hits. No asset files."""

import math
import random
from array import array

import pygame

RATE = 44100


def _sound(samples, volume):
    clipped = [max(-32767, min(32767, int(s * volume * 32767))) for s in samples]
    # Windows opens the mixer in stereo even when mono was requested. A mono
    # buffer is then read as left/right pairs, which plays every sound an octave high.
    channels = 1
    init = pygame.mixer.get_init()
    if init is not None:
        channels = init[2]
    if channels == 2:
        buf = array("h", (sample for sample in clipped for _ in (0, 1)))
    else:
        buf = array("h", clipped)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _tone(freq, duration, volume, decay):
    count = max(1, int(RATE * duration))
    buf = []
    for i in range(count):
        t = i / RATE
        env = math.exp(-decay * t) * min(1.0, i / 6)
        sample = math.sin(math.tau * freq * t) + 0.22 * math.sin(math.tau * freq * 2 * t)
        buf.append(sample * env)
    return _sound(buf, volume)


def _pair(first, second, volume):
    gap = int(RATE * 0.09)
    a = [0.0] * (int(RATE * 0.22) + gap)
    for freq, start in ((first, 0.0), (second, 0.09)):
        begin = int(start * RATE)
        count = int(0.16 * RATE)
        for i in range(count):
            at = begin + i
            if at >= len(a):
                break
            t = i / RATE
            env = math.exp(-7 * t) * min(1.0, i / 5)
            a[at] += math.sin(math.tau * freq * t) * env
    return _sound(a, volume)


def _noise(duration, volume, decay, seed):
    count = max(1, int(RATE * duration))
    rng = random.Random(seed)
    buf = []
    for i in range(count):
        env = math.exp(-decay * i / RATE) * min(1.0, i / 4)
        buf.append(rng.uniform(-1, 1) * env)
    return _sound(buf, volume)


class Audio:
    def __init__(self):
        self.muted = False
        self.ok = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(RATE, -16, 1, 512)
            self.ok = True
        except pygame.error:
            return
        self.sounds = {
            "hit_you": _tone(640, 0.06, 0.35, 28),
            "hit_ace": _tone(420, 0.07, 0.32, 24),
            "bounce": _tone(180, 0.05, 0.28, 36),
            "serve": _noise(0.05, 0.22, 28, 3),
            "net": _noise(0.09, 0.4, 18, 9),
            "out": _tone(140, 0.12, 0.3, 14),
            "score_you": _pair(523.25, 783.99, 0.34),
            "score_ace": _pair(392.0, 261.63, 0.32),
        }

    def play(self, name):
        if not self.ok or self.muted:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()
