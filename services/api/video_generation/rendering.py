import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class VideoRenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class SceneRenderInput:
    scene_no: int
    duration_seconds: int
    visual_path: Path
    visual_type: str
    narration_path: Path | None = None


def get_ffmpeg_executable():
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        executable = Path(get_ffmpeg_exe()).resolve()
    except (ImportError, OSError, RuntimeError):
        return None
    return executable if executable.is_file() else None


def get_local_render_capabilities():
    executable = get_ffmpeg_executable()
    return {
        "available": executable is not None,
        "engine": "ffmpeg" if executable else "",
    }


def _run_ffmpeg(executable, arguments, cwd, timeout_seconds):
    try:
        completed = subprocess.run(
            [str(executable), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *arguments],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        raise VideoRenderError("本地成片渲染超时，请缩短分镜时长后重试。") from error
    except OSError as error:
        raise VideoRenderError("无法启动本地 FFmpeg 渲染程序。") from error

    if completed.returncode != 0:
        raise VideoRenderError("本地 FFmpeg 渲染失败，请检查素材格式或字幕内容。")


def _segment_arguments(scene, output_name, width, height, fps, crf):
    duration = max(1, int(scene.duration_seconds))
    arguments = []
    if scene.visual_type == "image":
        arguments.extend(("-loop", "1", "-framerate", str(fps)))
    arguments.extend(("-i", str(scene.visual_path)))
    if scene.narration_path:
        arguments.extend(("-i", str(scene.narration_path)))
    else:
        arguments.extend(("-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"))

    video_filter = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},"
        f"tpad=stop_mode=clone:stop_duration={duration},trim=duration={duration},setpts=PTS-STARTPTS[v]"
    )
    audio_filter = (
        f"[1:a]aresample=48000,apad=pad_dur={duration},"
        f"atrim=0:{duration},asetpts=PTS-STARTPTS[a]"
    )
    arguments.extend(
        (
            "-filter_complex",
            f"{video_filter};{audio_filter}",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            output_name,
        )
    )
    return arguments


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as rendered_file:
        for chunk in iter(lambda: rendered_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_video_tail_frame(video_path, *, timeout_seconds, max_file_bytes):
    executable = get_ffmpeg_executable()
    if executable is None:
        raise VideoRenderError("服务端尚未安装可用的 FFmpeg 尾帧提取程序。")

    video_path = Path(video_path).resolve()
    if not video_path.is_file():
        raise VideoRenderError("待提取尾帧的视频文件不存在。")

    with tempfile.TemporaryDirectory(prefix="video-tail-frame-") as temporary_directory:
        workspace = Path(temporary_directory)
        output_name = "tail-frame.jpg"
        _run_ffmpeg(
            executable,
            (
                "-sseof",
                "-0.08",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                output_name,
            ),
            workspace,
            timeout_seconds,
        )
        output_path = workspace / output_name
        if not output_path.is_file():
            raise VideoRenderError("FFmpeg 未生成视频尾帧。")
        content = output_path.read_bytes()

    if not content.startswith(b"\xff\xd8\xff"):
        raise VideoRenderError("视频尾帧不是有效的 JPEG 文件。")
    if len(content) <= 0 or len(content) > max_file_bytes:
        raise VideoRenderError("视频尾帧为空或超过参考图大小限制。")
    return {
        "content": content,
        "mime_type": "image/jpeg",
        "extension": ".jpg",
        "file_size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def render_video_project(
    scenes,
    subtitle_path,
    output_path,
    *,
    width,
    height,
    fps,
    crf,
    timeout_seconds,
    max_file_bytes,
):
    executable = get_ffmpeg_executable()
    if executable is None:
        raise VideoRenderError("服务端尚未安装可用的 FFmpeg 渲染程序。")
    if not scenes:
        raise VideoRenderError("没有可用于成片渲染的分镜。")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_parent = output_path.parent / ".render-tmp"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    subtitle_mode = "none"

    with tempfile.TemporaryDirectory(prefix="video-render-", dir=temporary_parent) as temporary_directory:
        workspace = Path(temporary_directory)
        segment_names = []
        for scene in scenes:
            segment_name = f"segment-{scene.scene_no:02d}.mp4"
            _run_ffmpeg(
                executable,
                _segment_arguments(scene, segment_name, width, height, fps, crf),
                workspace,
                timeout_seconds,
            )
            segment_names.append(segment_name)

        manifest_path = workspace / "segments.txt"
        manifest_path.write_text("".join(f"file '{name}'\n" for name in segment_names), encoding="utf-8")
        assembled_name = "assembled.mp4"
        _run_ffmpeg(
            executable,
            ("-f", "concat", "-safe", "0", "-i", manifest_path.name, "-c", "copy", "-movflags", "+faststart", assembled_name),
            workspace,
            timeout_seconds,
        )

        rendered_path = workspace / "final.mp4"
        if subtitle_path:
            local_subtitle_path = workspace / "subtitles.srt"
            shutil.copyfile(subtitle_path, local_subtitle_path)
            subtitle_filter = (
                "subtitles=filename='subtitles.srt':"
                "force_style='FontName=Microsoft YaHei,FontSize=18,"
                "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=60'"
            )
            try:
                _run_ffmpeg(
                    executable,
                    (
                        "-i",
                        assembled_name,
                        "-vf",
                        subtitle_filter,
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-crf",
                        str(crf),
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "copy",
                        "-movflags",
                        "+faststart",
                        rendered_path.name,
                    ),
                    workspace,
                    timeout_seconds,
                )
                subtitle_mode = "burned_in"
            except VideoRenderError:
                _run_ffmpeg(
                    executable,
                    (
                        "-i",
                        assembled_name,
                        "-i",
                        local_subtitle_path.name,
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0",
                        "-map",
                        "1:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "copy",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        "language=zho",
                        "-movflags",
                        "+faststart",
                        rendered_path.name,
                    ),
                    workspace,
                    timeout_seconds,
                )
                subtitle_mode = "embedded"
        else:
            shutil.copyfile(workspace / assembled_name, rendered_path)

        file_size = rendered_path.stat().st_size
        if file_size <= 0 or file_size > max_file_bytes:
            raise VideoRenderError("本地成片文件为空或超过服务端大小限制。")
        with rendered_path.open("rb") as rendered_file:
            header = rendered_file.read(12)
        if len(header) < 12 or header[4:8] != b"ftyp":
            raise VideoRenderError("本地成片渲染结果不是有效的 MP4 文件。")

        temporary_output_path = output_path.with_name(f".{output_path.name}.tmp")
        try:
            shutil.copyfile(rendered_path, temporary_output_path)
            os.replace(temporary_output_path, output_path)
        finally:
            temporary_output_path.unlink(missing_ok=True)

    return {
        "file_size": output_path.stat().st_size,
        "sha256": _sha256_file(output_path),
        "subtitle_mode": subtitle_mode,
        "scene_count": len(scenes),
        "duration_seconds": sum(scene.duration_seconds for scene in scenes),
        "video_scene_count": sum(scene.visual_type == "video" for scene in scenes),
        "image_scene_count": sum(scene.visual_type == "image" for scene in scenes),
        "narration_scene_count": sum(scene.narration_path is not None for scene in scenes),
        "width": width,
        "height": height,
        "fps": fps,
        "crf": crf,
    }
