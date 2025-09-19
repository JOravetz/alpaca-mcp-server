#!/usr/bin/env python3
"""Generate Jessica's voice celebration for today's epic trading victory using Kokoro TTS."""

import numpy as np
from scipy.io.wavfile import write as write_wav
import onnxruntime
import json
from pathlib import Path

# Load Kokoro model and voices
sess_options = onnxruntime.SessionOptions()
model_path = Path("/home/jjoravet/alpaca-mcp-server-enhanced/kokoro.onnx")
onnx_sess = onnxruntime.InferenceSession(str(model_path), sess_options=sess_options)

# Load voice data
with open("/home/jjoravet/alpaca-mcp-server-enhanced/voices.bin", "rb") as f:
    voices = np.frombuffer(f.read(), dtype=np.float32).reshape(111, 256)

# Jessica's voice is af_jessica (index 3)
JESSICA_VOICE_ID = 3

def generate_speech(text, voice_id=JESSICA_VOICE_ID, output_file="jessica_victory_celebration.wav"):
    """Generate speech using Kokoro TTS with Jessica's voice."""

    # Prepare inputs
    text_array = np.array([[text]], dtype=object)
    voice_array = np.array([voices[voice_id]], dtype=np.float32)
    speed_array = np.array([1.0], dtype=np.float32)

    # Run inference
    audio = onnx_sess.run(
        None,
        {"text": text_array, "voice": voice_array, "speed": speed_array}
    )[0]

    # Convert to 16-bit PCM
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    audio_int16 = audio_int16.squeeze()

    # Save to WAV file
    write_wav(output_file, 24000, audio_int16)
    print(f"✅ Jessica's celebration saved to: {output_file}")

    return output_file

# Create Jessica's epic celebration message
celebration_text = """
Oh my goodness! What an absolutely INCREDIBLE trading day!
Eight thousand and forty dollars in pure profit!
That's over EIGHT THOUSAND DOLLARS in a single day!

You achieved a PERFECT one hundred percent win rate today!
Twenty-six winning trades and NOT A SINGLE LOSS!
This is absolutely legendary performance!

Your biggest winner was that brilliant CDLX short for twenty-six hundred dollars!
And look at AGMH, thirty-one trades generating over thirty-five hundred in profit!
Even the penny stocks like CJET contributed over a thousand dollars!

You traded over ONE POINT TWO MILLION dollars in volume today!
Fifty-six trades executed with surgical precision!
Every single position closed profitably!

This is what elite trading looks like!
Your aggressive strategy is working PERFECTLY!
Eight thousand dollars richer in just one day!

Keep this momentum going! You're absolutely crushing it!
This is just the beginning of something extraordinary!
Congratulations on this PHENOMENAL victory!
"""

if __name__ == "__main__":
    print("🎉 Generating Jessica's Victory Celebration Speech...")
    print("=" * 60)

    # Generate the speech
    output_file = generate_speech(celebration_text.strip())

    print("\n📊 Today's Trading Highlights:")
    print("  💰 Total P&L: +$8,040.15")
    print("  🎯 Win Rate: 100% (26/26 trades)")
    print("  📈 Total Volume: $1,202,436.86")
    print("  🏆 Biggest Win: $2,600 (CDLX short)")
    print("  🚀 Most Active: AGMH with 31 trades")
    print("\n🔊 Play the audio file to hear Jessica's celebration!")
    print(f"   Command: play {output_file}")