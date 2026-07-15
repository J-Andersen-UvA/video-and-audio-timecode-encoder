# video-and-audio-timecode-encoder & UnrealFBXTimecode Decoder

## 1 

This project provides a script to encode videos and generate a CSV file based on frame data and timecode. The script supports two types of timecode sources:

1. **Visible QR Code**: If the video contains a visible QR code displaying the timecode in the format `hours:minutes:seconds:milliseconds`, the script will read the QR code and generate the corresponding CSV file.
2. **Audio Channel**: If the video has an audio channel that contains the timecode, the script will process the audio and generate the CSV file accordingly.

This tool is useful for synchronizing video frames with precise timecodes, making it easier to analyze and process video data.

## 2

This project also provides a script to decode unreal FBX's with timecodes on the root bone of animations.
