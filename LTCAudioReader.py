import sounddevice as sd
import numpy as np
# import ltc_reader
import threading
from threading import Lock
import pyaudio
import wave
import ffmpeg
import csv
import audioop
import argparse
import os

class LTCVideoProcessor:
    """
    Class to process a video file, extract its audio, decode LTC timecode,
    and generate a CSV file with frame-to-timecode mapping.
    """

    def __init__(self, video_path, output_csv):
        self.video_path = video_path
        self.output_csv = output_csv
        self.audio_path = "temp_audio.wav"
        self.ltc_reader = LTCReader()
    
    def extract_audio(self):
        """
        Extracts audio from the video file and saves it as a temporary WAV file.
        """
        print("[INFO] Extracting audio from video...")
        try:
            (
                ffmpeg.input(self.video_path)
                .output(self.audio_path, format="wav", ac=1, ar="48000")
                .run(quiet=True, overwrite_output=True)
            )
        except ffmpeg.Error as e:
            print(f"[ERROR] Failed to extract audio: {e}")
            exit(1)

    def process_audio(self):
        """
        Reads the extracted audio file, decodes LTC timecode, and saves it to a CSV.
        """
        print("[INFO] Processing audio and extracting LTC timecodes...")

        # Open audio file
        wf = wave.open(self.audio_path, 'rb')
        frame_rate = wf.getframerate()
        num_frames = wf.getnframes()
        block_size = 2048
        
        timecode_data = []

        for i in range(0, num_frames, block_size):
            frames = wf.readframes(block_size)
            self.ltc_reader.decode_ltc(frames)
            tc = self.ltc_reader.get_tc()

            if tc:
                timestamp = i / frame_rate  # Approximate time in seconds
                timecode_data.append([timestamp, tc])

        # Save timecode data to CSV
        self.save_to_csv(timecode_data)
        print(f"[INFO] Timecode data saved to {self.output_csv}")

    def save_to_csv(self, timecode_data):
        """
        Saves extracted timecodes to a CSV file.
        """
        with open(self.output_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamps", "Timecodes"])
            writer.writerows(timecode_data)
    
    def remove_temp_audio(self):
        """
        Removes the temporary audio file.
        """
        try:
            os.remove(self.audio_path)
        except FileNotFoundError:
            pass

    def run(self):
        self.extract_audio()
        self.process_audio()
        self.remove_temp_audio()

class LTCReader:
    """
    This class is based on the original work by Alan Telles (https://github.com/alantelles/py-ltc-reader/tree/master).
    It has been altered to not use some variables and to be in a class form.
    """
    def __init__(self):
        self.FORMAT = pyaudio.paInt16
        self.SYNC_WORD = '0011111111111101'
        self.jam = '00:00:00:00'
        self.now_tc = '00:00:00:00'

    def bin_to_bytes(self, a,size=1):
        ret = int(a,2).to_bytes(size,byteorder='little')
        return ret

    def bin_to_int(self, a):
        out = 0
        for i,j in enumerate(a):
            out += int(j)*2**i
        return out

    def decode_ltc(self, wave_frames):
        frames = []
        output = ''
        last = None
        toggle = True
        sp = 1
        for i in range(0,len(wave_frames),2):
            data = wave_frames[i:i+2]
            pos = audioop.minmax(data,2)
            if pos[0] < 0:
                cyc = 'Neg'
            else:
                cyc = 'Pos'
            if cyc != last:
                if sp >= 7:
                    if sp > 14:
                        bit = '0'
                        output += str(bit)
                    else:
                        if toggle:
                            bit = '1'
                            output += str(bit)
                            toggle = False
                        else:
                            toggle = True
                    if len(output) >= len(self.SYNC_WORD):
                        if output[-len(self.SYNC_WORD):] == self.SYNC_WORD:
                            if len(output) > 80:
                                frames.append(output[-80:])
                                output = ''
                                self.jam = self.decode_frame(frames[-1])['formatted_tc']
                sp = 1
                last = cyc
            else:
                sp += 1

    def decode_frame(self, frame):
        o = {}
        o['frame_units'] = self.bin_to_int(frame[:4])
        o['user_bits_1'] = int.from_bytes(self.bin_to_bytes(frame[4:8]),byteorder='little')
        o['frame_tens'] = self.bin_to_int(frame[8:10])
        o['drop_frame'] = int.from_bytes(self.bin_to_bytes(frame[10]),byteorder='little')
        o['color_frame'] = int.from_bytes(self.bin_to_bytes(frame[11]),byteorder='little')
        o['user_bits_2'] = int.from_bytes(self.bin_to_bytes(frame[12:16]),byteorder='little')
        o['sec_units'] = self.bin_to_int(frame[16:20])
        o['user_bits_3'] = int.from_bytes(self.bin_to_bytes(frame[20:24]),byteorder='little')
        o['sec_tens'] = self.bin_to_int(frame[24:27])
        o['flag_1'] = int.from_bytes(self.bin_to_bytes(frame[27]),byteorder='little')
        o['user_bits_4'] = int.from_bytes(self.bin_to_bytes(frame[28:32]),byteorder='little')
        o['min_units'] = self.bin_to_int(frame[32:36])
        o['user_bits_5'] = int.from_bytes(self.bin_to_bytes(frame[36:40]),byteorder='little')
        o['min_tens'] = self.bin_to_int(frame[40:43])
        o['flag_2'] = int.from_bytes(self.bin_to_bytes(frame[43]),byteorder='little')
        o['user_bits_6'] = int.from_bytes(self.bin_to_bytes(frame[44:48]),byteorder='little')
        o['hour_units'] = self.bin_to_int(frame[48:52])
        o['user_bits_7'] = int.from_bytes(self.bin_to_bytes(frame[52:56]),byteorder='little')
        o['hour_tens'] = self.bin_to_int(frame[56:58])
        o['bgf'] = int.from_bytes(self.bin_to_bytes(frame[58]),byteorder='little')
        o['flag_3'] = int.from_bytes(self.bin_to_bytes(frame[59]),byteorder='little')
        o['user_bits_8'] = int.from_bytes(self.bin_to_bytes(frame[60:64]),byteorder='little')
        o['sync_word'] = int.from_bytes(self.bin_to_bytes(frame[64:],2),byteorder='little')
        o['formatted_tc'] = "{:02d}:{:02d}:{:02d}:{:02d}".format(
            o['hour_tens']*10+o['hour_units'],
            o['min_tens']*10+o['min_units'],
            o['sec_tens']*10+o['sec_units'],
            o['frame_tens']*10+o['frame_units'],
        )
        return o

    def get_tc(self):
        if self.jam:
            h, m, s, f = [int(x) for x in self.jam.split(':')]
            formatted_tc = "{:02d}:{:02d}:{:02d}:{:02d}".format(h, m, s, f)
            self.now_tc = formatted_tc
        return self.now_tc

class AudioReader:
    """
    Class to listen for Tentacle Sync timecode using sounddevice and ltc_reader.
    Singleton class to ensure only one instance is created.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AudioReader, cls).__new__(cls)
        return cls._instance

    def __init__(self, sample_rate=48000, channels=1, block_size=2048):
        if not hasattr(self, 'initialized'):
            self.sample_rate = sample_rate
            self.channels = channels
            self.block_size = block_size
            self.current_timecode = None
            self.stream = None
            self.initialized = True
            self.started = False
            self.LTCReader = LTCReader()

    def start(self):
        if self.started:
            return
        self.started = True
        p = pyaudio.PyAudio()
        self.stream = p.open(format=self.LTCReader.FORMAT,
                             channels=self.channels,
                             rate=self.sample_rate,
                             input=True,
                             frames_per_buffer=self.block_size)
        self.thread = threading.Thread(target=self._read_stream)
        self.thread.start()

    def _read_stream(self):
        while self.started:
            data = self.stream.read(self.block_size)
            self.LTCReader.decode_ltc(data)
            self.current_timecode = self.LTCReader.get_tc()
            if self.current_timecode:
                print("Timecode:\t", self.current_timecode)
            else:
                print("No LTC timecode detected in this frame.")

    def stop(self):
        if self.stream:
            self.started = False
            self.thread.join()
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            print("Stopped listening for Tentacle Sync timecode.")

    def get_current_timecode(self):
        return self.current_timecode

# # Example usage
# if __name__ == "__main__":
#     tentacle_sync = AudioReader()
#     tentacle_sync.start()
#     try:
#         while True:
#             pass
#     except KeyboardInterrupt:
#         tentacle_sync.stop()

if __name__ == "__main__":
    # Argument parser for command-line usage
    parser = argparse.ArgumentParser(description="Extract LTC timecode from a video file and save to CSV.")
    parser.add_argument("--video_path", help="Path to the input video file", required=True)
    parser.add_argument("--output_csv", help="Path to save the output CSV file", required=True)
    args = parser.parse_args()

    processor = LTCVideoProcessor(args.video_path, args.output_csv)
    processor.run()
