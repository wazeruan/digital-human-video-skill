---
name: digital-human-video
description: Create topic-matched cartoon avatars and short Chinese speaking videos with ImageGen plus Muse in Chrome, or this project's local pipeline. Use for end-to-end avatar production, not general video editing.
---

# Digital Human Video

Turn a topic and a short Chinese line into a topic-matched animated-avatar video. Choose the route the user requested; never switch between Muse and local inference silently. For requested Muse runs, keep character art, silent video, and spoken audio as separate assets, then combine them locally with FFmpeg before QA. Do not treat a solid-color backdrop as transparency.

## Fast path: transparent ImageGen → separate Muse assets → FFmpeg

1. **Intake once.** Use the topic and exact Chinese narration from the request. Keep each spoken line to 20 Unicode grapheme clusters, including punctuation. If topic or narration is missing, ask only for the missing item; do not invent production copy. Default to a warm, natural female Mandarin voice unless the user specified another voice.
2. **Choose or make one transparent avatar.** If the user wants the same character or series and a suitable approved transparent local avatar exists, reuse it. An image already in the selected Muse chat may be reused; a Codex/ChatGPT or project-folder image is not automatically visible to Muse. Otherwise use ImageGen once to create one original, topic-matched full-body cartoon presenter. Request a real transparent PNG/alpha channel—not a checkerboard or a picture of transparency—with no setting, floor, cast shadow, text, logo, watermark, or extra people. Put the topic cue on the outfit or a small accessory, not in a background. Keep the character 70–80% of a 16:9 frame with safe head/feet margins, face unobscured, eyes toward camera, relaxed lips, and hands slightly separated from the torso. Keep identity stable across a series; do not make unrequested variants.
3. **Verify and stage the image.** Check topic fit and face/hands/feet; verify the PNG really has transparent pixels/alpha before using it. If the image generator cannot provide transparency, stop and ask before using a separate background-removal step. Save the selected image to a unique ignored path such as `outputs/avatars/<topic-slug>/avatar.png`; do not overwrite an existing avatar.
4. **Generate the silent transparent video in Muse.** Use `mcp__cua_repl.js` on the user's explicitly selected Chrome tab. Confirm it is the intended Muse chat and leave unrelated tabs untouched. Before submitting, confirm Muse visibly supports genuine alpha/transparent video export; if that capability is unclear, ask first rather than spending credits to test it. Attach only the selected avatar and request one short silent video: preserve the character and alpha transparency on every frame; show only the character on an empty transparent canvas; add no room, scenery, floor, shadow, color fill, checkerboard, cuts, zoom, or on-screen text. Animate as if speaking the exact requested line, with natural modest mouth motion, steady gaze, slow subtle blinks, and one small topic-appropriate gesture; avoid redesign, exaggerated mouth/eyebrows, wandering eyes, and extra fingers. If Muse cannot produce a genuine alpha video, stop and ask whether the user wants a separate background-removal fallback. Do not silently accept an opaque or chroma-key version.
5. **Generate the voice as a separate Muse asset.** In a distinct audio-generation task, request one audio-only Mandarin voice recording of the exact line as WAV, or MP3 if WAV is unavailable, with the selected voice and pace, no music or sound effects, and no intro/outro. Do not rely on audio embedded in the video. If Muse cannot provide a separate audio file, ask before switching provider or route.
6. **Wait for both Muse tasks.** Track the single video job and the single audio job using fresh UI state; do not refresh, resend, or duplicate either generation. Check after about 10–15 seconds, then every 20–30 seconds while working; give a concise update if the wait exceeds a minute. A disconnected/offline label alone is not a blocker if the user explicitly said to use the composer. Stop and ask if Muse requires a purchase, upgrade, legal acceptance, new permission, or another unapproved action.
7. **Collect and inspect the separate assets.** Download the alpha video and audio through Muse's visible controls to a temporary review folder; verify they are non-empty. Use `ffprobe` to check duration, dimensions, codecs, audio stream, and alpha-capable pixel format. Inspect several frames composited over a checkerboard to verify real transparency and review identity, framing, mouth/eye motion, gesture, and artifacts. Listen to the voice or verify it with a reliable transcript. Do not claim lip-sync or transparency unless checked. If Muse flattened the background or omitted either asset, keep the source and ask before another paid generation or background-removal fallback.
8. **Mux the audio and video locally with FFmpeg.** Preserve the full spoken-audio duration and give the picture about 0.1 seconds of extra tail so `-shortest` cannot clip the final audio packet. Convert the genuine-alpha source to a ProRes 4444 MOV master without flattening its alpha (skip this conversion if Muse already returned ProRes 4444):

   ```bash
   ffmpeg -i muse-alpha-video.mov -an -vf format=yuva444p10le -c:v prores_ks -profile:v 4444 -alpha_bits 16 avatar-alpha.mov
   ```

   Verify that `avatar-alpha.mov` still contains transparency. When it is at least as long as the voice track, mux without re-encoding that video stream, for example:

   ```bash
   ffmpeg -i avatar-alpha.mov -i narration.wav \
     -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
     -shortest slide-ready-alpha.mov
   ```

   If durations differ, extend or trim the picture while preserving alpha to leave that small tail beyond the complete audio, then mux. Keep a ProRes 4444 `.mov` alpha master; do not convert it to ordinary H.264 `.mp4` and call it transparent. [FFmpeg's ProRes documentation](https://ffmpeg.org/ffmpeg-codecs.html#ProRes) describes its 4444 profile and alpha support. PowerPoint lists QuickTime `.mov` as a supported container but recommends H.264/AAC MP4, so test alpha playback in the user's actual slide app and platform before relying on it ([supported formats](https://support.microsoft.com/en-us/powerpoint/video-and-audio-file-formats-supported-in-powerpoint)). If that app cannot play alpha, ask what background (if any) they want for a compatibility copy.
9. **Verify and save the final slide asset.** Check the combined file has both video and audio streams and retains alpha; inspect it over a checkerboard and play it in the target slide app when available. Save the transparent avatar PNG, separate source audio/video, and combined `.mov` in a unique ignored folder such as `outputs/muse-<date>-<topic-slug>/`. Keep generated/private media out of commits and label Muse work as external/browser-generated.

### Reusable Muse prompt shape

Use separate concise prompts and keep the actual topic and narration exact:

**Silent video:** Use the attached PNG as the exact transparent character reference. Topic: **[topic]**. Animate the character as if saying “**[verbatim line]**” but generate no audio. Make one short full-body 16:9 clip with a locked camera, natural small mouth movement, steady eye contact, slow subtle facial motion, and one small open-palm gesture. Preserve true alpha transparency on every frame; show no background, room, floor, shadow, fill color, checkerboard, text, or extra people. No redesign, cuts, zoom, wandering eyes, or extra fingers. Return one silent alpha video file.

**Separate audio:** Say exactly in Mandarin: “**[verbatim line]**”, in a warm natural female voice at a clear moderate pace. Return one clean audio-only WAV (or MP3 if WAV is unavailable), without music, sound effects, intro, or outro.

For a same-topic series, cache and reuse the selected transparent avatar instead of regenerating it. For a genuinely new topic or character, make a new image once; do not create a new image merely because the narration changes.

## Browser and data boundaries

The Muse route sends the selected image and requested text to an external provider. Only a user request for this ImageGen→Muse workflow authorizes sending the image generated/selected for this run and its narration—not other portraits, voice recordings, credentials, project files, or conversation history. If uploading a local image, identify that exact file and destination. If Chrome's file chooser fails, do not weaken extension permissions or silently substitute an in-chat avatar. Tell the user: “To enable file upload, open `chrome://extensions`, click **Details** under the ChatGPT browser extension, and enable **Allow access to file URLs**.” See the [Chrome file-upload instructions](https://developers.openai.com/codex/app/chrome-extension#upload-files). Never change the permission yourself. Do not accept legal terms, buy credits, or upgrade plans without action-time approval; if the visible cost is not covered by the user's request or included balance, stop and ask.

## Local pipeline (only when requested)

Before setup, read the project README, `.env.example`, and third-party notices. Confirm Apple Silicon/macOS before recommending MLX/MPS, and use the documented Qwen3-TTS/MLX path for local Chinese speech. Run `scripts/demo_fake.sh` before installing model weights; for a real render, follow the pinned setup and checksum scripts, keep MuseTalk and LivePortrait in separate environments, and run only one render at a time on a 24GB Mac. Reuse the avatar preprocessing cache for a stable avatar; choose the cached LivePortrait loop when speech timing need not match the mouth, noting it is not waveform-driven. Choose MuseTalk only for requested approximate audio-driven lip motion and inspect cartoon faces for deformation. Keep the unauthenticated FastAPI service and MuseTalk sidecar on `127.0.0.1`. Until the detector licensing issue is resolved, use LivePortrait only with `--noncommercial-research` for genuinely non-commercial work. Report whether results were verified on real hardware or only through the fake/simulated path. If the user reports local video inference freezes the computer, stop and do not retry unless explicitly reauthorized.

## Release and commercial checks

Before packaging, inspect third-party notices and model terms. LivePortrait's license flags InsightFace detection models as non-commercial research only; commercial users must replace them with a commercially licensed detector or obtain permission. Never describe that setup as commercially cleared until the detector issue is resolved. For Muse, separately review provider terms for uploaded images/text, generated audio/video, commercial use, retention, and export. `BUYER-LICENSE.txt` grants only the purchasing customer use and private modification; it prohibits sharing, resale, and redistribution and must be included with every paid package. It does not grant rights to models, code, inputs, identities, voices, or outputs.
