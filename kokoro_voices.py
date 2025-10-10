# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "kokoro-onnx @ git+https://github.com/thewh1teagle/kokoro-onnx.git",
#     "soundfile>=0.12.0",
#     "numpy>=1.21.0"
# ]
# ///

import os
import numpy as np
import subprocess
from pathlib import Path

def get_kokoro_instance():
    from kokoro_onnx import Kokoro
    
    models_dir = Path.home() / ".kokoro_models" / "correct"
    model_path = models_dir / "model.onnx"
    voices_path = models_dir / "voices.bin"
    
    return Kokoro(str(model_path), str(voices_path))

def test_sexy_voices():
    kokoro = get_kokoro_instance()
    
    # Test message - Epic weekly profit celebration!
    text = "Oh my goodness! $98,895.97 in pure profit this week! You are an absolute trading legend! Your best performer was AIHS with $35,353.29! Keep riding this wave to financial freedom! WAY TO GO, JOEBOB!"
    
    # Sexy American female voices to test
    sexy_voices = [
        ("af_bella", "Bella - Expressive & sultry"),
        ("af_nova", "Nova - Modern & smooth"), 
        ("af_sarah", "Sarah - Warm & appealing"),
        ("af_jessica", "Jessica - Rich & mature"),
        ("af_heart", "Heart - Romantic & warm"),
        ("af_nicole", "Nicole - Sophisticated"),
        ("af_river", "River - Flowing & natural"),
        ("af_sky", "Sky - Light & dreamy")
    ]
    
    print("🎭 Testing sexy American female voices...")
    print("🔊 Listen and pick your favorite!\n")
    
    for voice_code, description in sexy_voices:
        try:
            print(f"🎵 Testing {voice_code}: {description}")
            
            # Generate audio
            audio, sample_rate = kokoro.create(text, voice=voice_code, speed=0.95)  # Slightly slower for sexier tone
            
            # Convert and save
            if not isinstance(audio, np.ndarray):
                audio = np.array(audio)
            if audio.ndim > 1:
                audio = audio.flatten()
            
            filename = f"sexy_{voice_code}.wav"
            import soundfile as sf
            sf.write(filename, audio, sample_rate)
            
            # Play the voice
            result = subprocess.run(["aplay", filename], timeout=10)
            
            if result.returncode == 0:
                print(f"✅ Played {voice_code}")
                
                # Pause between voices
                input(f"Press Enter to continue to next voice...")
                print()
            
        except Exception as e:
            print(f"❌ Error with {voice_code}: {e}")
    
    print("🎉 Voice test complete!")
    print("\nWhich voice did you like best? Update your hook with:")
    print('kokoro_tts(message, voice="YOUR_CHOICE", speed=0.95)')

def jessica_weekly_celebration():
    """Play Jessica's epic weekly profit celebration message"""
    kokoro = get_kokoro_instance()
    
    # Jessica's celebration message
    text = "Oh my goodness! $98,895.97 in pure profit this week! You are an absolute trading legend! Your best performer was AIHS with $35,353.29! Keep riding this wave to financial freedom! WAY TO GO, JOEBOB!"
    
    print("🎉 JESSICA'S WEEKLY CELEBRATION 🎉")
    print("💰 Playing epic profit celebration...")
    
    try:
        # Generate audio with Jessica's voice
        audio, sample_rate = kokoro.create(text, voice="af_jessica", speed=0.95)
        
        # Convert and save
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)
        if audio.ndim > 1:
            audio = audio.flatten()
        
        filename = "jessica_weekly_celebration.wav"
        import soundfile as sf
        sf.write(filename, audio, sample_rate)
        
        # Play the celebration
        result = subprocess.run(["aplay", filename], timeout=30)
        
        if result.returncode == 0:
            print("✅ Jessica's celebration played successfully!")
            print("🏆 Keep crushing those trades, champion!")
        
    except Exception as e:
        print(f"❌ Error playing celebration: {e}")

def jessica_todays_celebration():
    """Generate Jessica's celebration for today's epic profit"""
    kokoro = get_kokoro_instance()
    
    # Jessica's celebration message for today's P&L - $69,747.17
    text = (
        "Oh my goodness, JoeBob! $69,747.17 in pure profit TODAY! "
        "You are absolutely crushing it! "
        "Your best trade was MGIH with an incredible $162,945! "
        "That's a legendary single-day performance! "
        "92.9% win rate with 44 trades! "
        "You're on fire! Keep this momentum going, champion! "
        "Financial freedom is right around the corner! "
        "WAY TO GO, JOEBOB!"
    )
    
    print("🎉 JESSICA'S DAILY CELEBRATION 🎉")
    print("💰 Creating epic profit celebration audio...")
    
    try:
        # Generate audio with Jessica's voice
        audio, sample_rate = kokoro.create(text, voice="af_jessica", speed=0.95)
        
        # Convert and save
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)
        if audio.ndim > 1:
            audio = audio.flatten()
        
        filename = "jessica_todays_celebration.wav"
        import soundfile as sf
        sf.write(filename, audio, sample_rate)
        
        print(f"✅ Audio saved as {filename}")
        print("📊 Today's P&L: $69,747.17")
        print("🏆 Best Trade: MGIH +$162,945")
        print("🎯 Win Rate: 92.9%")
        
        # Play the celebration
        print("\n🔊 Playing celebration...")
        result = subprocess.run(["aplay", filename], timeout=30)
        
        if result.returncode == 0:
            print("✅ Jessica's celebration played successfully!")
            print("🚀 Keep crushing those trades, champion!")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error generating celebration: {e}")
        return None

def jessica_read_file(filename="jessica_real_message.txt"):
    """Have Jessica read any text file with proper celebration tone"""
    kokoro = get_kokoro_instance()

    print(f"🎉 JESSICA'S EPIC CELEBRATION 🎉")
    print(f"📖 Reading from: {filename}")

    try:
        # Read the message from file
        with open(filename, 'r') as f:
            text = f.read().strip()

        print("💰 Generating Jessica's celebration audio...")

        # Generate audio with Jessica's voice
        audio, sample_rate = kokoro.create(text, voice="af_jessica", speed=0.95)

        # Convert and save
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)
        if audio.ndim > 1:
            audio = audio.flatten()

        output_filename = "jessica_epic_celebration.wav"
        import soundfile as sf
        sf.write(output_filename, audio, sample_rate)

        print(f"✅ Audio saved as {output_filename}")

        # Play the celebration
        print("\n🔊 Playing Jessica's epic $20K celebration...")
        result = subprocess.run(["aplay", output_filename], timeout=60)

        if result.returncode == 0:
            print("✅ Jessica's celebration played successfully!")
            print("🚀 $20,140.03 - LEGENDARY STATUS ACHIEVED!")
            print("🏆 100% Win Rate - 33 Wins, 0 Losses!")
            print("💎 You are an absolute trading legend!")

        return output_filename

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def jessica_50k_celebration():
    """Generate Jessica's celebration for today's $50K profit"""
    kokoro = get_kokoro_instance()

    # Read jessica.txt and create celebration
    with open("jessica.txt", 'r') as f:
        content = f.read()

    # Jessica's epic $50K celebration message
    text = (
        "OH MY GOD, JoeBob! FIFTY THOUSAND AND FORTY-FOUR DOLLARS in pure profit TODAY! "
        "This is ABSOLUTELY LEGENDARY! "
        "100 percent win rate - PERFECT execution! "
        "SMLR crushed it with thirteen thousand six hundred eighty-four dollars! "
        "BOXL delivered twelve thousand four hundred sixty-four! "
        "HOUS was INCREDIBLE with over ten thousand in just THREE trades! "
        "You are UNSTOPPABLE! This is the kind of performance that builds EMPIRES! "
        "Keep this momentum going, champion! Financial freedom is HERE! "
        "WAY TO GO, JOEBOB!"
    )

    print("🎉 JESSICA'S $50K CELEBRATION 🎉")

    try:
        # Generate audio with Jessica's voice
        audio, sample_rate = kokoro.create(text, voice="af_jessica", speed=0.95)

        # Convert and save
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)
        if audio.ndim > 1:
            audio = audio.flatten()

        filename = "jessica_50k_celebration.wav"
        import soundfile as sf
        sf.write(filename, audio, sample_rate)

        print(f"✅ Audio saved as {filename}")

        # Play the celebration
        print("🔊 Playing Jessica's celebration...")
        subprocess.run(["aplay", filename], timeout=30)

        return filename

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def jessica_pnl_celebration():
    """Generate Jessica's celebration from today's P&L in jessica.txt"""
    kokoro = get_kokoro_instance()

    print("🎉 JESSICA'S P&L CELEBRATION 🎉")
    print("📖 Reading P&L message from jessica.txt...")

    try:
        # Read the complete message from jessica.txt
        with open("jessica.txt", 'r') as f:
            text = f.read().strip()

        print("💰 Generating celebration audio from jessica.txt...")

        # Generate audio with Jessica's voice
        audio, sample_rate = kokoro.create(text, voice="af_jessica", speed=0.95)

        # Convert and save
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)
        if audio.ndim > 1:
            audio = audio.flatten()

        filename = "jessica_pnl_celebration.wav"
        import soundfile as sf
        sf.write(filename, audio, sample_rate)

        print(f"✅ Audio saved as {filename}")

        # Play the celebration
        print("\n🔊 Playing Jessica's celebration...")
        result = subprocess.run(["aplay", filename], timeout=300)

        if result.returncode == 0:
            print("✅ Jessica's celebration played successfully!")
            print("🚀 Celebration complete!")

        return filename

    except Exception as e:
        print(f"❌ Error generating celebration: {e}")
        return None

def jessica_362k_week_celebration():
    """Generate Jessica's EPIC celebration for the $362K+ weekly profit"""
    kokoro = get_kokoro_instance()

    # Jessica's EPIC $362K weekly celebration message
    text = (
        "OH MY GOD, JoeBob! THREE HUNDRED SIXTY-TWO THOUSAND, EIGHT HUNDRED SIXTEEN DOLLARS! "
        "IN ONE WEEK! This is ABSOLUTELY LEGENDARY! This is the kind of week that CHANGES LIVES! "
        "Let me break down this INCREDIBLE achievement! "
        "Monday was PERFECT - Fifty-three thousand, nine hundred forty-three dollars with a FLAWLESS one hundred percent win rate! "
        "Tuesday delivered ANOTHER fifty-eight thousand, four hundred seventy-eight dollars! "
        "But Wednesday? Wednesday was ABSOLUTELY INSANE! ONE HUNDRED SIXTY-ONE THOUSAND dollars in a SINGLE DAY! "
        "RKDA crushed it with sixty-nine thousand! ASTX delivered another thirty thousand! "
        "Thursday brought thirty-seven thousand, and Friday? Friday you closed with ANOTHER fifty-one thousand! "
        "Your average daily profit was over SEVENTY-TWO THOUSAND DOLLARS! "
        "Ninety-two point six percent win rate across FOUR HUNDRED THIRTY-ONE TRADES! "
        "You traded FORTY-SEVEN MILLION DOLLARS in volume this week! "
        "JoeBob, you are NOT just a trader anymore - you are a LEGEND! "
        "This is the kind of performance that builds EMPIRES! "
        "This is the kind of week that makes HISTORY! "
        "Keep this UNSTOPPABLE momentum going! Financial freedom isn't coming - IT'S HERE! "
        "WAY TO GO, CHAMPION!"
    )

    print("🎉 JESSICA'S EPIC $362K WEEK CELEBRATION 🎉")
    print("💰 Creating legendary celebration audio...")

    try:
        # Generate audio with Jessica's voice
        audio, sample_rate = kokoro.create(text, voice="af_jessica", speed=0.95)

        # Convert and save
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)
        if audio.ndim > 1:
            audio = audio.flatten()

        filename = "jessica_362k_week_celebration.wav"
        import soundfile as sf
        sf.write(filename, audio, sample_rate)

        print(f"✅ Audio saved as {filename}")
        print("📊 Weekly P&L: $362,816.82")
        print("🏆 Best Day: Wednesday $161,098.07")
        print("🎯 Win Rate: 92.6%")
        print("💎 Total Trades: 431")
        print("💰 Total Volume: $47.7M")

        # Play the celebration
        print("\n🔊 Playing Jessica's EPIC celebration...")
        result = subprocess.run(["aplay", filename], timeout=60)

        if result.returncode == 0:
            print("✅ Jessica's celebration played successfully!")
            print("🚀 YOU ARE A LEGEND, JOEBOB!")

        return filename

    except Exception as e:
        print(f"❌ Error generating celebration: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "celebrate":
        jessica_weekly_celebration()
    elif len(sys.argv) > 1 and sys.argv[1] == "today":
        jessica_todays_celebration()
    elif len(sys.argv) > 1 and sys.argv[1] == "milestone":
        jessica_read_file("jessica_real_message.txt")
    elif len(sys.argv) > 1 and sys.argv[1] == "50k":
        jessica_50k_celebration()
    elif len(sys.argv) > 1 and sys.argv[1] == "pnl":
        jessica_pnl_celebration()
    elif len(sys.argv) > 1 and sys.argv[1] == "362k":
        jessica_362k_week_celebration()
    else:
        test_sexy_voices()
