import sounddevice as sd
import numpy as np
import pyaudio
import wave
import ffmpeg
import csv
import audioop
import argparse
import os

class LTCVideoProcessor:
    """
    Processes a video file, extracts its audio, decodes LTC timecode,
    and generates a CSV file in DaVinci Resolve format.
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
    
    def get_frame_rate(self):
        """Returns the frame rate of the video."""
        try:
            probe = ffmpeg.probe(self.video_path)
            return int(probe["streams"][0]["r_frame_rate"].split("/")[0])
        except ffmpeg.Error as e:
            print(f"[ERROR] Failed to get frame rate: {e}")
            exit(1)

    def process_audio(self):
        """
        Reads the extracted audio file, decodes LTC timecode, and saves it to a DaVinci Resolve CSV.
        """
        print("[INFO] Processing audio and extracting LTC timecodes...")

        # Open audio file
        wf = wave.open(self.audio_path, 'rb')
        frame_rate = self.get_frame_rate()
        print(f"[INFO] Frame rate: {frame_rate}")
        num_frames = wf.getnframes()
        block_size = 2048

        video_filename = os.path.basename(self.video_path)
        video_dir = os.path.dirname(self.video_path)

        timecode_data = []

        prev_timecode = None
        start_frame = None

        for i in range(0, num_frames, block_size):
            frames = wf.readframes(block_size)
            self.ltc_reader.decode_ltc(frames)
            tc = self.ltc_reader.get_tc()

            # If timecode is 00:00:00:00, skip
            if tc == '00:00:00:00':
                continue

            if tc:
                samples_per_frame = wf.getframerate() / frame_rate
                current_frame = int(i / samples_per_frame)  # Correct frame number

                if prev_timecode is None:
                    # First timecode detected
                    prev_timecode = tc
                    start_frame = current_frame
                elif tc != prev_timecode:
                    # Save previous segment
                    timecode_data.append([
                        video_filename, video_dir, "", frame_rate, "48000", "2", "", "PCM", "",
                        prev_timecode, tc, start_frame, current_frame - 1, (current_frame - start_frame),
                        "16", "", "", "16", ""
                    ])
                    # Start new segment
                    prev_timecode = tc
                    start_frame = current_frame

        # Save last segment
        if prev_timecode:
            timecode_data.append([
                video_filename, video_dir, "", frame_rate, "48000", "2", "", "PCM", "",
                prev_timecode, prev_timecode, start_frame, num_frames - 1, (num_frames - start_frame),
                "16", "", "", "16", ""
            ])

        # Save to CSV
        self.save_to_csv(timecode_data)
        print(f"[INFO] DaVinci Resolve CSV saved to {self.output_csv}")

    def save_to_csv(self, timecode_data):
        """
        Saves extracted timecodes to a DaVinci Resolve-compatible CSV file.
        """
        headers = [
            "File Name", "Clip Directory", "Duration TC", "Frame Rate", "Audio Sample Rate", 
            "Audio Channels", "Resolution", "Video Codec", "Audio Codec", 
            "Start TC", "End TC", "Start Frame", "End Frame", "Frames", 
            "Bit Depth", "Field Dominance", "Data Level", "Audio Bit Depth", "Date Modified"
        ]

        with open(self.output_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(timecode_data)
    
    def remove_temp_audio(self):
        """Removes the temporary audio file."""
        try:
            os.remove(self.audio_path)
        except FileNotFoundError:
            pass

    def run(self):
        """Executes the full process: extract, decode, and save timecodes."""
        self.extract_audio()
        self.process_audio()
        self.remove_temp_audio()

class LTCReader:
    """
    Decodes Linear Timecode (LTC) from audio frames.
    """

    def __init__(self):
        self.FORMAT = pyaudio.paInt16
        self.SYNC_WORD = '0011111111111101'
        self.jam = '00:00:00:00'
        self.now_tc = '00:00:00:00'

    def bin_to_int(self, a):
        return sum(int(j) * 2**i for i, j in enumerate(a))

    def decode_ltc(self, wave_frames):
        """Extracts LTC timecode from audio frames."""
        output = ''
        last = None
        toggle = True
        sp = 1

        for i in range(0, len(wave_frames), 2):
            data = wave_frames[i:i+2]
            pos = audioop.minmax(data, 2)
            cyc = 'Neg' if pos[0] < 0 else 'Pos'

            if cyc != last:
                if sp >= 7:
                    if sp > 14:
                        output += '0'
                    else:
                        output += '1' if toggle else ''
                        toggle = not toggle

                    if len(output) >= len(self.SYNC_WORD):
                        if output[-len(self.SYNC_WORD):] == self.SYNC_WORD:
                            if len(output) > 80:
                                self.jam = self.decode_frame(output[-80:])['formatted_tc']
                sp = 1
                last = cyc
            else:
                sp += 1

    def decode_frame(self, frame):
        """Decodes an 80-bit LTC frame and extracts a formatted timecode."""
        return {
            'formatted_tc': "{:02d}:{:02d}:{:02d}:{:02d}".format(
                self.bin_to_int(frame[56:58]) * 10 + self.bin_to_int(frame[48:52]),
                self.bin_to_int(frame[40:43]) * 10 + self.bin_to_int(frame[32:36]),
                self.bin_to_int(frame[24:27]) * 10 + self.bin_to_int(frame[16:20]),
                self.bin_to_int(frame[8:10]) * 10 + self.bin_to_int(frame[:4]),
            )
        }

    def get_tc(self):
        """Returns the latest detected timecode."""
        return self.jam if self.jam else self.now_tc

# Command-line execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract LTC timecode from a video file and save to DaVinci Resolve CSV.")
    parser.add_argument("--video_path", help="Path to the input video file", required=True)
    parser.add_argument("--output_csv", help="Path to save the output CSV file", required=True)
    args = parser.parse_args()

    processor = LTCVideoProcessor(args.video_path, args.output_csv)
    processor.run()
