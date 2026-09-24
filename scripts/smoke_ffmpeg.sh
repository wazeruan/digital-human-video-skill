#!/usr/bin/env bash
set -euo pipefail

for command_name in ffmpeg ffprobe; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: $command_name" >&2
    exit 1
  fi
done

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/digital-human-ffmpeg.XXXXXX")"
trap 'rm -rf "$temp_dir"' EXIT

ffmpeg -hide_banner -loglevel error \
  -f lavfi -i 'color=c=0x90b8e8:s=320x240:r=24:d=3' \
  -an -c:v libx264 -pix_fmt yuv420p "$temp_dir/silent.mp4"
ffmpeg -hide_banner -loglevel error \
  -f lavfi -i 'sine=frequency=440:sample_rate=24000:duration=2' \
  -c:a pcm_s16le "$temp_dir/narration.wav"
ffmpeg -hide_banner -loglevel error \
  -stream_loop -1 -i "$temp_dir/silent.mp4" -i "$temp_dir/narration.wav" \
  -map 0:v:0 -map 1:a:0 -t 2 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -movflags +faststart "$temp_dir/final.mp4"

video_codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$temp_dir/final.mp4")"
audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$temp_dir/final.mp4")"
duration="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$temp_dir/final.mp4")"

if [[ "$video_codec" != "h264" || "$audio_codec" != "aac" ]]; then
  echo "Unexpected output streams: video=$video_codec audio=$audio_codec" >&2
  exit 1
fi
if ! awk -v duration="$duration" 'BEGIN { exit !(duration >= 1.9 && duration <= 2.1) }'; then
  echo "Unexpected output duration: $duration seconds" >&2
  exit 1
fi

echo "FFmpeg smoke test passed: H.264 + AAC, ${duration}s."
