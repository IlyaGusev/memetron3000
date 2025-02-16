import subprocess

import fire  # type: ignore


def compress_video(
    input_path: str, output_path: str, target_size_mb: float = 0.7, max_width: int = 640
) -> str:
    # Get video information using ffprobe
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,duration",
        "-of",
        "json",
        str(input_path),
    ]

    probe_output = subprocess.check_output(probe_cmd)
    video_info = eval(probe_output.decode("utf-8"))

    # Calculate video bitrate for target size
    duration = float(video_info["streams"][0]["duration"])
    target_size_bits = target_size_mb * 8 * 1024 * 1024  # Convert MB to bits
    video_bitrate = int(target_size_bits / duration * 0.95)  # Leave 5% for audio

    # Calculate new dimensions maintaining aspect ratio
    orig_width = int(video_info["streams"][0]["width"])
    orig_height = int(video_info["streams"][0]["height"])

    if orig_width > max_width:
        new_width = max_width
        new_height = int(orig_height * (max_width / orig_width))
        new_height -= new_height % 2  # Ensure height is even
    else:
        new_width = orig_width
        new_height = orig_height

    # Compression command
    compress_cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "28",
        "-b:v",
        f"{video_bitrate}",
        "-maxrate",
        f"{video_bitrate * 1.2}",  # Allow some flexibility in bitrate
        "-bufsize",
        f"{video_bitrate}",
        "-vf",
        f"scale={new_width}:{new_height},fps=16",
        "-c:a",
        "aac",
        "-b:a",
        "48k",  # Decent audio quality
        "-y",  # Overwrite output file if it exists
        str(output_path),
    ]

    # Execute compression
    subprocess.run(compress_cmd, check=True)
    return str(output_path)


if __name__ == "__main__":
    fire.Fire(compress_video)
