# Digital Human Video Skill — Muse Workflow

这个仓库只保留基于 Codex、ImageGen、Muse 浏览器操作和 FFmpeg 的数字人视频 skill。工作流是：按主题生成一张角色图，经 Chrome 的 computer-use 将图和提示词提交给 Muse，分别生成静音视频和语音，下载后用本机 FFmpeg 合成为最终视频并质检。

**没有本地 TTS、视频推理、FastAPI 服务或模型权重。** FFmpeg 只用于检查媒体、修整静音视频并合并音视频；Muse 的生成能力在外部服务中完成。本次通过普通提交清除最新版本中的旧本地实现，不改写公开历史；较早的提交仍可能包含旧源码和头像样例。

## 需要准备

- Codex 桌面端，并可使用 ImageGen 和 computer-use。
- Chrome 中打开并登录到用户指定的 Muse 页面；生成时只操作该页面。
- 本机安装 FFmpeg 与 `ffprobe`。macOS 可运行 `brew install ffmpeg`；其他系统请使用各自包管理器的 FFmpeg 构建。
- 如需安装 skill：标准 shell、`cp` 和 `zip`。

不需要 Python/uv 环境、不下载模型，也不需要启动服务。

## 安装 skill

```bash
./scripts/install_skill.sh
```

脚本会将 `skills/digital-human-video` 复制到 Codex skills 目录。如果目标已存在，脚本会停止，不覆盖现有安装。之后在 Codex 中使用 `$digital-human-video`，或提出数字人视频制作请求。

## 生成流程

Skill 会按每次需求决定画风、主题、构图、时长、语音、语气、面部/身体动作、背景、字幕和交付格式；不会固定成卡通、全身或某个声音。文案保持原样。未指定时长时，根据文案和语速估算，优先用实际生成语音时长确定最终视频时长。

1. 用 ImageGen 生成或复用符合主题的角色图。
2. 在 Muse 中提交图片和静音视频提示词；另开独立任务生成精确文案的语音。支持时并行等待两个任务。
3. 下载并检查素材；用 FFmpeg 按语音时长修整/循环静音视频并合并音频。
4. 检查成片画面、面部动作、背景、音轨和时长，再存到本机唯一输出目录。

透明背景只在用户确实需要且 Muse/输出格式支持时请求，并检查真实 alpha；不能把纯色背景或棋盘格图案当作透明。详细提示词、等待和质检规则见 [SKILL.md](skills/digital-human-video/SKILL.md)。

## 最小本机检查

```bash
ffmpeg -version
ffprobe -version
./scripts/smoke_ffmpeg.sh
```

该检查只用本机合成的测试图像与音调验证 FFmpeg 合成路径，不会调用 Muse、消耗服务额度或证明生成质量。

检查 skill 安装包：

```bash
./scripts/package_skill.sh /tmp/digital-human-video.zip
unzip -t /tmp/digital-human-video.zip
```

真正的端到端验证需要在 Codex 中运行 skill、由 Muse 生成并下载一对素材，再检查本机合并后的成片；CI 不会自动登录或生成外部媒体。

## 隐私和商业边界

选择经授权的人像与声音。通过 Muse 工作流提交时，图像和文案会发送给外部服务；不要附带无关人物图像、凭据、项目文件或对话记录。不要未经授权模仿真实人物、接受法律条款或购买额度。购买许可仅限购买者本人使用和私下修改，禁止分享、转售与再分发；这份草案还需法律审阅。查看 [SECURITY.md](SECURITY.md)、[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、[COMMERCIAL_CLEARANCE.md](COMMERCIAL_CLEARANCE.md) 和 [RELEASE.md](RELEASE.md)。
