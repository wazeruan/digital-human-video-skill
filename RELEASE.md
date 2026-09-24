# Release checklist

This project distributes a Muse-through-browser Codex skill. The latest tree has no local inference app, model downloads, or sample media. The publishing cleanup is a fast-forward commit: older public Git history is intentionally preserved and may still contain files from the former local implementation. In particular, reachable history currently contains `examples/avatar.png`, `examples/avatar-cartoon.png`, and `examples/avatar-fullbody.png` without allowlisted provenance receipts. `scripts/release_audit.py --release` will block a paid package on those historical images. Do not bypass that check or add them to an allowlist without verified provenance. Removing them from public history would require a separately approved history rewrite.

## Public source update

1. Review the exact staged changes and ensure no user media, credentials, model binaries, or generated outputs are included.
2. Run `python3 scripts/release_audit.py`, `bash -n scripts/*.sh`, and `./scripts/smoke_ffmpeg.sh` on a machine with FFmpeg.
3. Build and inspect the skill archive:

   ```bash
   ./scripts/package_skill.sh /tmp/digital-human-video.zip
   unzip -t /tmp/digital-human-video.zip
   unzip -l /tmp/digital-human-video.zip
   ```

4. Check the GitHub Actions package and smoke checks. Publish only a fast-forward update to the intended repository and verify its name, visibility, default branch, and package contents.

## Paid distribution

1. Keep `skills/digital-human-video/BUYER-LICENSE.txt` in every package. It is a draft and must be reviewed by counsel before taking payment.
2. Complete `COMMERCIAL_CLEARANCE.md` with evidence for provider terms, inputs and consent, model/service outputs, and the intended sales market.
3. Do not bundle source images, audio, generated videos, model weights, provider code, or FFmpeg binaries unless their rights and license obligations are separately cleared.
4. Only then may an owner deliberately update the clearance status and run the manual/tagged commercial release gate: `python3 scripts/release_audit.py --release --commercial`.

The FFmpeg smoke flow only confirms that a local test clip can be muxed; it does not establish that Muse is reachable, that provider terms permit a use, or that any generated result meets quality expectations.
