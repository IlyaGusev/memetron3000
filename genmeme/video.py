from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip  # type: ignore


def create_meme_video(video_path: str, output_path: str, caption_text: str) -> None:
    video = VideoFileClip(video_path)
    video_width: int = video.size[0]
    video_height: int = video.size[1]

    desired_box_height = video_height // 7 * 2
    padding = desired_box_height // 5
    initial_font_size = 50

    font_size = initial_font_size
    while True:
        text_clip = TextClip(
            caption_text,
            font="Impact",
            fontsize=font_size,
            color="white",
            size=(video_width - padding * 2, None),
            method="caption",
            align="center",
        ).set_duration(video.duration)
        if text_clip.size[1] + (padding * 2) <= desired_box_height:
            break
        font_size -= 5
        if font_size < 20:
            font_size = 20
            break

    text_y_position = (desired_box_height - text_clip.size[1]) // 2 + padding // 2 + 10
    text_bg_height = (desired_box_height + padding // 2) // 2 * 2

    text_clip = text_clip.set_position(("center", text_y_position))
    text_bg = ColorClip(
        size=(video_width, text_bg_height), color=(0, 0, 0)
    ).set_duration(video.duration)

    final_height = video_height + text_bg_height
    base_layer = ColorClip(
        size=(video_width, final_height), color=(0, 0, 0)
    ).set_duration(video.duration)
    final = CompositeVideoClip(
        [
            base_layer,
            text_bg,
            text_clip,
            video.set_position((0, text_bg_height)),  # Position video below caption
        ],
    ).subclip(0, min(video.duration, 13))

    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=16,
        threads=32,
        preset="ultrafast",
        ffmpeg_params=[
            "-movflags",
            "faststart",
            "-metadata",
            "handler_name=VideoHandler",
        ],
    )
    video.close()
    final.close()


if __name__ == "__main__":
    create_meme_video(
        "videos/scary_cat.mp4",
        "output/scary_cat_output.mp4",
        "Годовой план работы, который нужно сдать в понедельник, пока я смотрю 5й видос с котиками в воскресенье вечером:",
    )
