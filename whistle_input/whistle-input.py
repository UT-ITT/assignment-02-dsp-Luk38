import sounddevice as sd
import numpy as np
import pynput
from pynput.keyboard import Key, Controller
import time

# Keyboard controller for simulating key presses
keyboard = Controller()

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024 # Number of audio frames per buffer
RATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audio
AMPLITUDE_THRESHOLD = 1 # Minimum amplitude to consider a note detected

# global variables
detected_frequency = 0.0
frequency_history = []
last_trigger = 0.0
whistle = False

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

    # whistle range
    mask = (freqs > 500) & (freqs < 4000)
    freqs = freqs[mask]
    amplitude = amplitude[mask]

    if np.max(amplitude) < AMPLITUDE_THRESHOLD:
        return 0.0

    # Index of the peak frequency
    peak_index = np.argmax(amplitude)

    # Return the frequency with highest amplitude
    return freqs[peak_index]

# audio callback to safe data
def audio_callback(indata, frames, time_info, status):
    global detected_frequency, last_trigger
    if status:
        print(status)

    data = indata[:, 0]  # mono

    # get detected frequency from audio data
    detected_frequency = get_frequency(data, RATE)

    # Don't append frequencies of 0
    if detected_frequency > 0:
        frequency_history.append(detected_frequency)
    else:
        return


    # Keep only the last 9 frequencies for analysis
    if len(frequency_history) > 10:
        frequency_history.pop(0)

    # Detect Chirps Up or Down based on frequency changes
    if len(frequency_history) >= 8: # need at least 10 frequencies to compare
        if time.time() - last_trigger > 1: # prevent too frequent triggers
            diff = np.mean(frequency_history[-4:]) - np.mean(frequency_history[:4]) # compare average of last and first 4 frequencies
            if abs(diff) > 50: #50 Hz threshold for detecting a chirp
                if diff > 0:
                    print("Up")
                    keyboard.press(Key.up)
                    keyboard.release(Key.up)
                else:
                    print("Down")
                    keyboard.press(Key.down)
                    keyboard.release(Key.down)
                frequency_history.clear() # clear history after detecting a chirp
                last_trigger = time.time()



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
    while True:
        time.sleep(0.01)