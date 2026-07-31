import io
import math
import sys
import wave
from array import array
from difflib import SequenceMatcher


AUDIO_QUALITY_VERSION = "1.0"
SPEECH_QUALITY_VERSION = "1.0"
MIN_SAMPLE_RATE = 16000
MIN_DURATION_SECONDS = 0.3
MIN_RMS_DBFS = -42.0
SILENCE_BLOCK_DBFS = -45.0
MAX_SILENCE_RATIO = 0.8
MAX_CLIPPING_RATIO = 0.03
ANALYSIS_BLOCK_MILLISECONDS = 20
READ_FRAMES_PER_CHUNK = 4096


def _issue(code, severity, message):
    return {"code": code, "severity": severity, "message": message}


def _dbfs(amplitude, full_scale):
    if amplitude <= 0 or full_scale <= 0:
        return -120.0
    return max(-120.0, 20 * math.log10(amplitude / full_scale))


def _decode_pcm_samples(raw_data, sample_width):
    if sample_width == 1:
        return [value - 128 for value in raw_data]
    if sample_width == 2:
        samples = array("h")
        samples.frombytes(raw_data)
    elif sample_width == 4:
        samples = array("i")
        samples.frombytes(raw_data)
    elif sample_width == 3:
        samples = []
        for offset in range(0, len(raw_data) - 2, 3):
            value = int.from_bytes(raw_data[offset : offset + 3], byteorder="little", signed=False)
            samples.append(value - (1 << 24) if value & (1 << 23) else value)
        return samples
    else:
        raise ValueError("unsupported_sample_width")
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def _failed_report(code, message):
    return {
        "version": AUDIO_QUALITY_VERSION,
        "status": "failed",
        "issues": [_issue(code, "error", message)],
        "metrics": {},
    }


def analyze_wav_audio(content, target_duration_seconds):
    try:
        with wave.open(io.BytesIO(content), "rb") as audio_file:
            channels = audio_file.getnchannels()
            sample_width = audio_file.getsampwidth()
            sample_rate = audio_file.getframerate()
            frame_count = audio_file.getnframes()
            compression_type = audio_file.getcomptype()
            if compression_type != "NONE":
                return _failed_report("unsupported_compression", "旁白 WAV 必须使用未压缩 PCM 编码。")
            if channels not in (1, 2):
                return _failed_report("unsupported_channels", "旁白 WAV 仅支持单声道或双声道。")
            if sample_width not in (1, 2, 3, 4):
                return _failed_report("unsupported_sample_width", "旁白 WAV 使用了不支持的采样位宽。")
            if sample_rate <= 0 or frame_count <= 0:
                return _failed_report("empty_audio", "旁白 WAV 不包含可分析的音频帧。")

            full_scale = float((1 << (sample_width * 8 - 1)) - 1)
            silence_threshold = full_scale * (10 ** (SILENCE_BLOCK_DBFS / 20))
            block_sample_count = max(channels, int(sample_rate * ANALYSIS_BLOCK_MILLISECONDS / 1000) * channels)
            sample_count = 0
            sum_squares = 0.0
            peak_amplitude = 0
            clipping_samples = 0
            silence_blocks = 0
            analyzed_blocks = 0
            current_block_count = 0
            current_block_sum_squares = 0.0

            while True:
                raw_data = audio_file.readframes(READ_FRAMES_PER_CHUNK)
                if not raw_data:
                    break
                try:
                    samples = _decode_pcm_samples(raw_data, sample_width)
                except ValueError:
                    return _failed_report("unsupported_sample_width", "旁白 WAV 使用了不支持的采样位宽。")
                for sample in samples:
                    amplitude = abs(sample)
                    square = float(sample) * float(sample)
                    sample_count += 1
                    sum_squares += square
                    peak_amplitude = max(peak_amplitude, amplitude)
                    if amplitude >= full_scale * 0.99:
                        clipping_samples += 1
                    current_block_count += 1
                    current_block_sum_squares += square
                    if current_block_count >= block_sample_count:
                        block_rms = math.sqrt(current_block_sum_squares / current_block_count)
                        if block_rms < silence_threshold:
                            silence_blocks += 1
                        analyzed_blocks += 1
                        current_block_count = 0
                        current_block_sum_squares = 0.0

            if current_block_count:
                block_rms = math.sqrt(current_block_sum_squares / current_block_count)
                if block_rms < silence_threshold:
                    silence_blocks += 1
                analyzed_blocks += 1
    except (EOFError, wave.Error):
        return _failed_report("invalid_wav", "旁白配音文件不是有效的 WAV 音频。")

    if sample_count <= 0:
        return _failed_report("empty_audio", "旁白 WAV 不包含可分析的音频采样。")

    duration_seconds = frame_count / sample_rate
    rms_amplitude = math.sqrt(sum_squares / sample_count)
    rms_dbfs = _dbfs(rms_amplitude, full_scale)
    peak_dbfs = _dbfs(peak_amplitude, full_scale)
    silence_ratio = silence_blocks / analyzed_blocks if analyzed_blocks else 1.0
    clipping_ratio = clipping_samples / sample_count
    metrics = {
        "duration_seconds": round(duration_seconds, 3),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bits": sample_width * 8,
        "rms_dbfs": round(rms_dbfs, 2),
        "peak_dbfs": round(peak_dbfs, 2),
        "silence_ratio": round(silence_ratio, 4),
        "clipping_ratio": round(clipping_ratio, 4),
    }
    issues = []
    if sample_rate < MIN_SAMPLE_RATE:
        issues.append(_issue("sample_rate_too_low", "error", "旁白采样率低于 16kHz，清晰度不足。"))
    if duration_seconds < MIN_DURATION_SECONDS:
        issues.append(_issue("audio_too_short", "error", "旁白音频过短，无法形成可用语音。"))
    duration_tolerance = max(0.75, float(target_duration_seconds or 0) * 0.2)
    if target_duration_seconds and duration_seconds > float(target_duration_seconds) + duration_tolerance:
        issues.append(_issue("audio_too_long", "error", "旁白时长超过镜头容限，进入成片后会被截断。"))
    if rms_dbfs < MIN_RMS_DBFS:
        issues.append(_issue("audio_too_quiet", "error", "旁白整体响度过低，无法清楚辨听。"))
    if silence_ratio > MAX_SILENCE_RATIO:
        issues.append(_issue("excessive_silence", "error", "旁白静音占比过高，疑似生成了空白或不完整音频。"))
    elif silence_ratio > 0.6:
        issues.append(_issue("high_silence_ratio", "warning", "旁白停顿较多，建议试听确认节奏。"))
    if clipping_ratio > MAX_CLIPPING_RATIO:
        issues.append(_issue("audio_clipping", "error", "旁白存在明显削波失真，请降低音量后重新生成。"))
    elif clipping_ratio > 0.01:
        issues.append(_issue("audio_clipping_risk", "warning", "旁白接近削波上限，建议试听确认音质。"))

    return {
        "version": AUDIO_QUALITY_VERSION,
        "status": "failed" if any(issue["severity"] == "error" for issue in issues) else "passed",
        "issues": issues,
        "metrics": metrics,
    }


def _normalize_speech_text(value):
    return "".join(character.lower() for character in str(value or "") if character.isalnum())


def build_speech_quality_report(expected_text, transcript, model, minimum_similarity):
    normalized_expected = _normalize_speech_text(expected_text)
    normalized_transcript = _normalize_speech_text(transcript)
    similarity = (
        SequenceMatcher(None, normalized_expected, normalized_transcript).ratio()
        if normalized_expected and normalized_transcript
        else 0.0
    )
    passed = bool(normalized_expected and normalized_transcript and similarity >= minimum_similarity)
    issues = []
    if not normalized_transcript:
        issues.append(_issue("empty_transcript", "warning", "ASR 未识别出有效旁白文本，请人工试听确认。"))
    elif not passed:
        issues.append(_issue("transcript_mismatch", "warning", "ASR 转写与计划旁白差异较大，请人工试听确认。"))
    return {
        "version": SPEECH_QUALITY_VERSION,
        "status": "passed" if passed else "needs_review",
        "source": "glm_asr",
        "model": model,
        "transcript": str(transcript or "").strip()[:2000],
        "similarity": round(similarity, 4),
        "minimum_similarity": minimum_similarity,
        "issues": issues,
    }


def build_pending_speech_quality_report(reason):
    reason_messages = {
        "asr_not_configured": "ASR 语音转写未启用，请人工试听确认。",
        "asr_limits_exceeded": "音频超过 ASR 文件限制，请人工试听确认。",
        "asr_request_failed": "ASR 语音转写暂不可用，请人工试听确认。",
    }
    return {
        "version": SPEECH_QUALITY_VERSION,
        "status": "needs_review",
        "source": "manual",
        "model": "",
        "transcript": "",
        "similarity": None,
        "minimum_similarity": None,
        "issues": [
            _issue(
                reason,
                "warning",
                reason_messages.get(reason, "旁白需要人工试听确认。"),
            )
        ],
    }
