import sys
import queue
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

OUT_PATH = Path("input/live_recording.wav")
SAMPLE_RATE = 16000   # 音声認識向けで十分
CHANNELS = 1          # モノラル
DTYPE = "int16"       # wav保存しやすい

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("🎤 Enterで録音開始...")
    input()

    q = queue.Queue()
    frames = []

    def callback(indata, frames_count, time, status):
        if status:
            print("audio status:", status, file=sys.stderr)
        q.put(indata.copy())

    print("● 録音中... Enterで停止")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        callback=callback,
        blocksize=1024,
    ):
        # Enterが押されるまで溜める
        try:
            while True:
                if msvcrt_kbhit_enter():
                    break
                try:
                    data = q.get(timeout=0.1)
                    frames.append(data)
                except queue.Empty:
                    pass
        except KeyboardInterrupt:
            print("\n⏹ Ctrl+C で停止")

        # 残りキューも回収
        while not q.empty():
            frames.append(q.get())

    if not frames:
        print("⚠️ 録音データがありません。")
        return

    audio = np.concatenate(frames, axis=0)
    sf.write(str(OUT_PATH), audio, SAMPLE_RATE)

    sec = len(audio) / SAMPLE_RATE
    print(f"✅ 保存: {OUT_PATH} ({sec:.1f}s)")

def msvcrt_kbhit_enter():
    # Windows向け: Enter押下検出
    try:
        import msvcrt
    except ImportError:
        return False

    hit = False
    while msvcrt.kbhit():
        ch = msvcrt.getwch()
        hit = True
        if ch in ("\r", "\n"):
            return True
    return False and hit

if __name__ == "__main__":
    main()