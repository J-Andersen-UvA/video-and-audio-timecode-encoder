import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path


DEFAULT_VIDEO = Path("Input/testJoseFR_260508_3_h264.mp4")


def run_ffprobe(video_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-of",
        "json",
        str(video_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def parse_rate(rate_text):
    if not rate_text or rate_text == "0/0":
        raise ValueError("No usable frame rate found in video stream.")
    return Fraction(rate_text)


def parse_timecode(timecode):
    separator = ";" if ";" in timecode else ":"
    parts = timecode.replace(";", ":").split(":")
    if len(parts) != 4:
        raise ValueError(f"Unsupported timecode format: {timecode}")
    hours, minutes, seconds, frames = [int(part) for part in parts]
    return hours, minutes, seconds, frames, separator


def timecode_to_frames(timecode, fps):
    hours, minutes, seconds, frames, _ = parse_timecode(timecode)
    return (((hours * 60 + minutes) * 60 + seconds) * fps) + frames


def frames_to_timecode(frame_number, fps, separator):
    frames_per_hour = fps * 60 * 60
    frames_per_minute = fps * 60

    hours, remainder = divmod(frame_number, frames_per_hour)
    minutes, remainder = divmod(remainder, frames_per_minute)
    seconds, frames = divmod(remainder, fps)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{frames:02d}"


def find_video_stream(streams):
    for stream in streams:
        if stream.get("codec_type") == "video":
            return stream
    raise ValueError("No video stream found.")


def find_embedded_timecode(streams):
    for stream in streams:
        tags = stream.get("tags") or {}
        if tags.get("timecode"):
            return tags["timecode"]
    raise ValueError("No embedded timecode tag found.")


def get_frame_count(video_stream, fps):
    if video_stream.get("nb_frames"):
        return int(video_stream["nb_frames"])
    if video_stream.get("duration"):
        return round(float(video_stream["duration"]) * fps)
    raise ValueError("No frame count or duration found in video stream.")


def main():
    parser = argparse.ArgumentParser(
        description="Print the embedded start and end timecode for an MP4."
    )
    parser.add_argument(
        "video",
        nargs="?",
        type=Path,
        default=DEFAULT_VIDEO,
        help=f"MP4 file to inspect. Defaults to {DEFAULT_VIDEO}",
    )
    args = parser.parse_args()

    probe = run_ffprobe(args.video)
    streams = probe.get("streams", [])
    video_stream = find_video_stream(streams)
    start_timecode = find_embedded_timecode(streams)

    frame_rate = parse_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))
    if frame_rate.denominator != 1:
        raise ValueError(f"Only whole-number frame rates are supported by this script, got {frame_rate}.")

    fps = frame_rate.numerator
    frame_count = get_frame_count(video_stream, fps)
    _, _, _, _, separator = parse_timecode(start_timecode)

    start_frame = timecode_to_frames(start_timecode, fps)
    end_frame = start_frame + frame_count - 1
    end_timecode = frames_to_timecode(end_frame, fps, separator)

    print(f"File: {args.video}")
    print(f"Frame rate: {fps} fps")
    print(f"Frames: {frame_count}")
    print(f"Start TC: {start_timecode}")
    print(f"End TC:   {end_timecode}")


if __name__ == "__main__":
    main()
