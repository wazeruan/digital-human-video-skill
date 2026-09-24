# Security and privacy boundary

This is a local, single-user prototype for a trusted Apple Silicon Mac. It is
not designed for internet-facing, shared-host, or multi-tenant deployment.

- The documented API entry point binds to `127.0.0.1` and uses one worker. Keep
  it there. Do not expose port 8000 or the MuseTalk sidecar port 8001 through
  `0.0.0.0`, a reverse proxy, a tunnel, or port forwarding.
- The API has no user authentication or per-user access control. Other
  processes running as the same local user can access it. Do not run it on a
  shared/untrusted account or use it as a remotely accessible service.
- Face images, job text, synthesized audio, intermediate renders, final MP4s,
  and SQLite job state persist under the configured `DIGITAL_HUMAN_DATA_DIR`
  (default `./data`). Keep this folder private and manage retention/backups
  yourself; the current MVP does not implement TTL, quotas, or deletion APIs.
  Newly created app directories/files use owner-only permissions where the
  filesystem supports them. Existing operator-supplied paths are never chmod'd;
  the service warns if they are accessible to group/others. Check permissions
  yourself, especially on external, network, or exFAT volumes.
- `POST /v1/avatars/generate` sends its prompt to the configured OpenAI API.
  The upload, TTS, animation, and composition paths otherwise run locally after
  required models are installed.
- Only process images and driving videos you own or are authorized to use. Get
  consent for identifiable faces and voices. Do not use the pipeline for
  non-consensual impersonation, fraud, or deceptive claims about real people.
- Model installers execute downloaded dependencies and load PyTorch checkpoints.
  Use the pinned setup scripts, verify their checksums, and review the upstream
  terms. The LivePortrait installer is explicitly limited to non-commercial
  research because its detector weights have that restriction.

If you find a security issue in a public copy of this repository, use GitHub's
private security reporting channel when available. Do not post faces, API keys,
model files, or exploit details in a public issue.
