import cv2
import pandas as pd
import numpy as np
from pyzbar.pyzbar import decode
import argparse
import re
import os

class QRExtractor:
    """Extracts QR codes from video frames."""
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.frame_rate = int(self.cap.get(cv2.CAP_PROP_FPS))
        self.resolution = f"{int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def extract_frames(self):
        """Yields frames from the video."""
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            timestamp = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000  # Timestamp in seconds
            yield frame, timestamp
        self.cap.release()

class QRProcessor:
    """Processes frames to extract QR code timecodes."""
    def extract_qr_timecode(self, frame):
        """Decodes QR code from the frame and returns extracted timecode."""
        qr_codes = decode(frame)
        for qr in qr_codes:
            if qr.type == 'QRCODE':
                qr_data = qr.data.decode("utf-8").strip()
                qr_data = self.fix_qr_data(qr_data)
                if self.is_valid_timecode(qr_data):
                    return qr_data
        return None

    def fix_qr_data(self, qr_data):
        if qr_data.startswith("[") and qr_data.endswith("]"):
            qr_data = qr_data[1:-1]
        if qr_data.startswith('"') and qr_data.endswith('"'):
            qr_data = qr_data[1:-1]
        return qr_data

    def is_valid_timecode(self, data):
        """Validates if the extracted data is a timecode format HH:MM:SS:FF."""
        return bool(re.match(r"\d{2}:\d{2}:\d{2}:\d{2}", data))

class VideoQRTimecodeProcessor:
    """Combines QR extraction & processing to generate a CSV formatted for DaVinci Resolve."""
    def __init__(self, video_path, output_csv):
        self.video_path = video_path
        self.output_csv = output_csv
        self.qr_extractor = QRExtractor(video_path)
        self.qr_processor = QRProcessor()

    def process_video(self):
        """Processes video and saves timecodes to CSV in DaVinci Resolve format."""
        video_filename = os.path.basename(self.video_path)
        video_dir = os.path.dirname(self.video_path)
        
        frame_rate = self.qr_extractor.frame_rate
        resolution = self.qr_extractor.resolution

        # Prepare CSV header
        headers = [
            "File Name", "Clip Directory", "Duration TC", "Frame Rate", "Audio Sample Rate", 
            "Audio Channels", "Resolution", "Video Codec", "Audio Codec", 
            "Start TC", "End TC", "Start Frame", "End Frame", "Frames", 
            "Bit Depth", "Field Dominance", "Data Level", "Audio Bit Depth", "Date Modified"
        ]

        data = []

        prev_timecode = None
        start_frame = None

        for frame, timestamp in self.qr_extractor.extract_frames():
            timecode = self.qr_processor.extract_qr_timecode(frame)
            current_frame = int(timestamp * frame_rate)

            if timecode:
                if prev_timecode is None:
                    # First clip
                    prev_timecode = timecode
                    start_frame = current_frame
                elif timecode != prev_timecode:
                    # Save previous segment
                    data.append([
                        video_filename, video_dir, "", frame_rate, "48000", "2", resolution, "H.264", "AAC",
                        prev_timecode, timecode, start_frame, current_frame - 1, (current_frame - start_frame),
                        "8", "", "Legal", "16", ""
                    ])
                    # Start new segment
                    prev_timecode = timecode
                    start_frame = current_frame

        # Save last segment
        if prev_timecode:
            data.append([
                video_filename, video_dir, "", frame_rate, "48000", "2", resolution, "H.264", "AAC",
                prev_timecode, prev_timecode, start_frame, self.qr_extractor.total_frames - 1, (self.qr_extractor.total_frames - start_frame),
                "8", "", "Legal", "16", ""
            ])

        # Save to CSV
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(self.output_csv, index=False)

        print(f"[INFO] DaVinci Resolve CSV saved to {self.output_csv}")

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract QR timecode from a video file and save to DaVinci Resolve CSV.")
    parser.add_argument("--video_path", help="Path to the input video file", required=True)
    parser.add_argument("--output_csv", help="Path to save the output CSV file", required=True)
    args = parser.parse_args()

    processor = VideoQRTimecodeProcessor(args.video_path, args.output_csv)
    processor.process_video()
