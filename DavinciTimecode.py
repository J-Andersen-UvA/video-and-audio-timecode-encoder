import pandas as pd

# filepath: C:/Users/VICON/Desktop/Code/timecodeReader/DavinciTimecode.py

class DaVinciCSVWriter:
    """Handles writing data to a CSV file in DaVinci Resolve format."""
    def __init__(self, output_csv):
        self.output_csv = output_csv
        self.headers = [
            "File Name", "Clip Directory", "Duration TC", "Frame Rate", "Audio Sample Rate",
            "Audio Channels", "Resolution", "Video Codec", "Audio Codec",
            "Start TC", "End TC", "Start Frame", "End Frame", "Frames",
            "Bit Depth", "Field Dominance", "Data Level", "Audio Bit Depth", "Date Modified"
        ]
        self.data = []

    def add_entry(self, video_filename, video_dir, frame_rate, resolution, start_tc, end_tc, start_frame, end_frame, frames):
        """Adds a new entry to the CSV data."""
        self.data.append([
            video_filename, video_dir, "", frame_rate, "48000", "2", resolution, "H.264", "AAC",
            start_tc, end_tc, start_frame, end_frame, frames,
            "8", "", "", "16", ""
        ])

    def save_to_csv(self):
        """Saves the collected data to the CSV file."""
        df = pd.DataFrame(self.data, columns=self.headers)
        df.to_csv(self.output_csv, index=False)
        print(f"[INFO] DaVinci Resolve CSV saved to {self.output_csv}")

# # example usage
# if __name__ == "__main__":
#     video_filename = "example_video.mp4"
#     video_dir = "C:/Users/VICON/Desktop/Code/timecodeReader"
#     output_csv = "output.csv"
#     frame_rate = 30  # Example frame rate
#     resolution = "1920x1080"  # Example resolution
#     start_tc = "00:00:00:00"  # Example start timecode
#     end_tc = "00:00:10:00"  # Example end timecode
#     start_frame = 0  # Example start frame
#     end_frame = 300  # Example end frame
#     frames = end_frame - start_frame + 1  # Calculate total frames

#     writer = DaVinciCSVWriter(output_csv)
#     writer.add_entry(video_filename, video_dir, frame_rate, resolution, start_tc, end_tc, start_frame, end_frame, frames)
#     writer.save_to_csv()