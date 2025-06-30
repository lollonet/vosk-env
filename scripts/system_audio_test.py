#!/usr/bin/env python3
"""
Test different audio capture methods to trigger system mic indicator
"""

import subprocess
import threading
import time
import sys

def test_parecord():
    """Test using parecord (PulseAudio) which should show mic icon"""
    print("🎤 Testing parecord (should show mic icon in tray)...")
    print("Speak for 5 seconds...")
    
    # This should trigger the system mic indicator
    cmd = ["parecord", "--format=s16le", "--rate=16000", "--channels=1", "/tmp/test_parecord.wav"]
    
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    
    time.sleep(5)  # Record for 5 seconds
    process.terminate()
    process.wait()
    
    print("✅ parecord test completed")
    print("💡 Did you see the mic icon in the system tray?")

def test_arecord():
    """Test using arecord (ALSA) which might show mic icon"""
    print("🎤 Testing arecord (might show mic icon)...")
    print("Speak for 5 seconds...")
    
    cmd = ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "/tmp/test_arecord.wav"]
    
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    
    time.sleep(5)  # Record for 5 seconds
    process.terminate()
    process.wait()
    
    print("✅ arecord test completed")
    print("💡 Did you see the mic icon in the system tray?")

def main():
    print("🔍 Testing different audio capture methods...")
    print("Watch your system tray for microphone indicators!")
    print()
    
    try:
        test_parecord()
        print()
        print("⏱️  Waiting 3 seconds before next test...")
        time.sleep(3)
        test_arecord()
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        subprocess.run(["rm", "-f", "/tmp/test_parecord.wav", "/tmp/test_arecord.wav"], 
                      stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()