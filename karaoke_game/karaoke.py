import sounddevice as sd
import numpy as np
import pyglet
import mido
from mido import MidiFile
import time

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024 # Number of audio frames per buffer
RATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audio
AMPLITUDE_THRESHOLD = 1 # Minimum amplitude to consider a note detected

# Pyglet window settings
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
# Colors
BACKGROUND_COLOR = (34, 45, 34) 

# simple song 
SONG_NOTES = [
    (2.0, 60),
    (4.0, 60),
    (6.0, 67),
    (8.0, 67),
    (10.0, 69),
    (12.0, 69),
    (14.0, 67),
    (16.0, 65),
    (18.0, 64),
    (20.0, 64),
    (22.0, 62),
    (24.0, 62),
    (26.0, 60),
    (28.0, 67),
    (30.0, 65),
    (32.0, 60),
]
NOTE_DURATION = 2.0 # seconds

# global variables
detected_frequency = 0.0
target_frequency = 0.0
note_hit = False
score = 0
start_time = None
current_index = 0

# print info about audio devices

print("Available input devices:\n")
devices = sd.query_devices()

input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"{i}: {dev['name']}")
        input_devices.append(i)

# let user select audio device
input_device = int(input("\nSelect input device: "))

# get frequency from audio data 
def get_frequency(data, rate):

    # Apply Hanning window to reduce spectral leakage
    window = np.hanning(len(data))
    data = data * window

    # Fast Fourier Transformation to get frequency spectrum
    fft_result = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1/rate)
    # Get the amplitude/magnitude of each frequency
    amplitude = np.abs(fft_result)

    # voice range
    mask = (freqs > 80) & (freqs < 1000)
    freqs = freqs[mask]
    amplitude = amplitude[mask]

    if np.max(amplitude) < AMPLITUDE_THRESHOLD:
        return 0.0

    # Index of the peak frequency
    peak_index = np.argmax(amplitude)

    # Return the frequency with highest amplitude
    return freqs[peak_index]

# compare two frequencies with a given tolerance (20Hz default)
def compare_frequencies(detected_freq, target_freq, tolerance=20):
    return abs(detected_freq - target_freq) <= tolerance

# transform MIDI note to frequency
def note_to_frequency(note):
    return 440 * (2 ** ((note - 69) / 12))

# audio callback to safe data and compare with target frequency
def audio_callback(indata, frames, time, status):
    global detected_frequency
    if status:
        print(status)

    data = indata[:, 0]  # mono

    # get detected frequency from audio data
    detected_frequency = get_frequency(data, RATE)
    print(f"Detected frequency: {detected_frequency:.2f} Hz")

# Game update function
def update(dt):
    global current_index, note_hit, score, target_frequency

    # exceptions for when game is not started or already finished
    if start_time is None:
        return

    t = time.time() - start_time

    if current_index >= len(SONG_NOTES):
        return

    note_time, note = SONG_NOTES[current_index]

    # check if current time is within the note duration
    if note_time <= t < note_time + NOTE_DURATION:
        target_frequency = note_to_frequency(note)

        if not note_hit and compare_frequencies(detected_frequency, target_frequency):
            score += 1
            note_hit = True
    else:
        target_frequency = 0.0

    # update to next note if current note duration has passed
    if t >= note_time + NOTE_DURATION:
        current_index += 1
        note_hit = False

window = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT)

@window.event
def on_draw():
    pyglet.gl.glClearColor(
        BACKGROUND_COLOR[0] / 255,
        BACKGROUND_COLOR[1] / 255,
        BACKGROUND_COLOR[2] / 255,
        1.0,)
    window.clear()
    label = pyglet.text.Label(
        f"Score: {score}\nFreq: {detected_frequency:.1f}\nTarget: {target_frequency:.1f}",
        x=20, y=WINDOW_HEIGHT -50
    )
    label.draw()

# open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS,
    samplerate=RATE,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    latency='low'
)

# continously capture and plot audio signal
with stream:
    print("\nStreaming... (Ctrl+C to stop)")
    start_time = time.time()
    pyglet.clock.schedule_interval(update, 1/60)
    pyglet.app.run()