#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "kokoro-onnx @ git+https://github.com/thewh1teagle/kokoro-onnx.git",
#     "soundfile>=0.12.0",
#     "numpy>=1.21.0"
# ]
# ///

"""Generate Jessica's voice celebration for today's EPIC $8,040.15 victory!"""

import numpy as np
import soundfile as sf
from pathlib import Path
from kokoro_onnx import Kokoro

def generate_victory_speech():
    # Initialize Kokoro with model paths
    models_dir = Path.home() / ".kokoro_models" / "correct"
    model_path = models_dir / "model.onnx"
    voices_path = models_dir / "voices.bin"

    kokoro = Kokoro(str(model_path), str(voices_path))

    # Create Jessica's epic celebration message
    celebration_text = """
    Oh my God! What an absolutely PHENOMENAL trading day!
    Eight thousand and forty dollars in pure profit!
    EIGHT THOUSAND DOLLARS in a single day!

    You achieved a PERFECT one hundred percent win rate today!
    Twenty-six winning trades and NOT A SINGLE LOSS!
    This is absolutely LEGENDARY performance!

    Your biggest winner was that brilliant CDLX short for twenty-six hundred dollars!
    And AGMH! Thirty-one trades generating over thirty-five hundred in profit!
    Even the penny stocks like CJET contributed over a thousand dollars!

    You traded over ONE POINT TWO MILLION dollars in volume today!
    Fifty-six trades executed with surgical precision!
    Every single position closed profitably!

    This is what ELITE trading looks like!
    Your aggressive strategy is working PERFECTLY!
    Eight thousand dollars richer in just one day!

    Keep this momentum going! You're absolutely CRUSHING IT!
    This is just the beginning of something extraordinary!
    Congratulations on this PHENOMENAL victory, champion!
    """

    print("🎉 Generating Jessica's Epic Victory Celebration...")
    print("=" * 60)

    # Generate audio with Jessica's voice (af_jessica)
    audio, sample_rate = kokoro.create(
        celebration_text.strip(),
        voice="af_jessica",
        speed=0.95  # Slightly slower for emphasis
    )

    # Save to file
    output_file = "jessica_todays_epic_victory.wav"
    sf.write(output_file, audio, sample_rate)

    print(f"\n✅ Victory celebration saved to: {output_file}")
    print("\n📊 Today's Trading Highlights:")
    print("  💰 Total P&L: +$8,040.15")
    print("  🎯 Win Rate: 100% (26/26 winning trades)")
    print("  📈 Total Volume: $1,202,436.86")
    print("  🏆 Biggest Win: $2,600 (CDLX short)")
    print("  🚀 Most Active: AGMH with 31 trades (+$3,557.43)")
    print("\n🔊 Playing Jessica's celebration now...")

    # Play the audio
    import subprocess
    try:
        subprocess.run(["play", output_file], check=False)
    except:
        print(f"   Manual play command: play {output_file}")

    return output_file

if __name__ == "__main__":
    generate_victory_speech()