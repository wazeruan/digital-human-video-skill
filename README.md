# Local Digital Human MVP (Apple Silicon)

面向 **24GB Apple Silicon Mac** 的短中文数字人 MVP：

```text
头像 PNG（上传或 OpenAI Images）
  -> 一次性规范化与缓存（可选 LivePortrait 全脸动作）
  -> Qwen3-TTS / MLX（本地中文语音）
  -> MuseTalk 1.5 / MPS sidecar（本地口型）
  -> FFmpeg（H.264/AAC MP4）
  -> FastAPI
```

单句限制为 20 个 Unicode 字素（标点也计数）。服务使用单 worker、单渲染队列，避免 24GB 统一内存被多个模型副本占满。头像以内容哈希缓存；同一头像只做一次静态视频预处理，MuseTalk sidecar 会按同一个 `avatar_key` 复用 bbox、mask、latent 等内存缓存。

这是**本机单用户预览 pipeline**，不是可直接部署到公网的多租户服务。`digital-human-api` 和 MuseTalk sidecar 默认只监听 loopback；不要用 `--host 0.0.0.0`、反向代理或端口转发公开它们。服务没有账户系统、租户隔离、配额或 TTL。头像、任务音频和视频会留在本地 `data/` 目录，直到用户自行管理；详情见 [SECURITY.md](SECURITY.md)。

## Codex skill

仓库内含 `skills/digital-human-video`，用于按此 pipeline 搭建、运行和验收短中文数字人视频。安装至本机 Codex skills 目录：

```bash
./scripts/install_skill.sh
```

若该目录已存在，先保留或移走旧版本再安装。可用 `scripts/package_skill.sh` 生成独立 ZIP，其中含买家许可说明。项目源码按根目录的专有声明公开供查看；这不等于允许使用或再分发。买家许可仅授予购买方使用和私下修改，禁止分享、转售或再分发；只有在发布历史、素材清点、商用清权和目标硬件真模型验收都通过后，才能作为可销售版本。目前商用清权与 24GB Mac 真模型验收仍未完成。

## 为什么分成两个环境

当前 `mlx-audio==0.5.4` 需要 Transformers 5.x，而实用的 MuseTalk macOS 端口固定在 Transformers 4.x。把两者装在一个 Python 环境会冲突，因此：

- 主环境：FastAPI、MLX/Qwen3-TTS、缓存、FFmpeg 编排
- `vendor/musetalk-mac/.venv`：MuseTalk 1.5、PyTorch/MPS、MediaPipe sidecar
- `vendor/LivePortrait/.venv`：LivePortrait、PyTorch/MPS；独立于 TTS 和 MuseTalk

官方 MuseTalk 仍以 CUDA/Linux 为主要路径；这里的 macOS 端口是第三方实现，已固定到项目中记录的 commit，但不受 MuseTalk 上游维护或验证。

## 0. 系统要求

- Apple Silicon，macOS 14+
- Python 3.11、[`uv`](https://docs.astral.sh/uv/)
- FFmpeg：`brew install ffmpeg`
- 首次下载模型约需要数 GB 空间和网络

## 1. 安装主服务

```bash
uv sync --frozen --extra tts --extra test
cp .env.example .env
```

先跑不下载模型的完整流程：

```bash
DIGITAL_HUMAN_BACKEND=fake uv run pytest
./scripts/demo_fake.sh /path/to/your-authorized-avatar.png "欢迎来到我的频道"
```

`fake` 会生成可播放的测试 MP4，但只有静态头像和测试音；它用于验证 API、缓存和 FFmpeg，不冒充真实数字人口型。

## 2. 安装 MuseTalk 1.5 MPS sidecar

```bash
./scripts/setup_musetalk_mac.sh
```

脚本会克隆并固定 [musetalk-mac](https://github.com/barnent1/musetalk-mac) 到已核验的 commit，创建独立 Python 3.11 环境并下载权重。启动 sidecar 时推荐使用 8001 端口，主 API 使用 8000。

该固定版本的 `.gitignore` 会误漏掉 `musetalk/models` 两个推理模块；安装脚本会从本项目内已审查的 MPS 安全补丁恢复它们，因此不要跳过安装脚本而手工只克隆仓库。

24GB Mac 从 batch size 4 开始；确认内存有余量后再试 8。不要使用该端口在 M3 Ultra 上展示的 batch size 16 作为 24GB 默认值。

## 3. 启动真实服务

编辑 `.env`：

```dotenv
DIGITAL_HUMAN_BACKEND=local
DIGITAL_HUMAN_MUSETALK_URL=http://127.0.0.1:8001
DIGITAL_HUMAN_QWEN_MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit
DIGITAL_HUMAN_QWEN_REVISION=049ef77fe8816b536193c0c25f9a214d17921282
DIGITAL_HUMAN_DEFAULT_VOICE=Vivian
```

运行（必须单 worker）：

```bash
uv run digital-human-api
```

安装完成后，一条命令跑真实的本地演示（会按需启动两个服务）：

```bash
./scripts/demo_local.sh /path/to/your-authorized-avatar.png "欢迎来到我的频道"
```

成功结果写入 `outputs/final-local.mp4`。

## 4. 让卡通人物的全脸动起来

准备一张你有权使用的正面头像：五官清楚、眼睛看镜头、嘴部自然闭合、无脸部遮挡。公开的发布包不会捆绑本地测试中使用的人像或生成头像。

LivePortrait 用有眨眼、眉毛和轻微头动的 driving video 驱动整张脸；MuseTalk 可进一步生成口型，但卡通头像上可能出现嘴部变形，效果需人工验收。该组合的默认 InsightFace 检测权重只允许非商业研究，未清权版本不能销售或商用。研究测试才安装：

```bash
./scripts/setup_liveportrait_mac.sh --noncommercial-research
```

然后在 `.env` 中配置：

```dotenv
DIGITAL_HUMAN_BACKEND=local
DIGITAL_HUMAN_MOTION_BACKEND=liveportrait
DIGITAL_HUMAN_LIVEPORTRAIT_DIR=./vendor/LivePortrait
DIGITAL_HUMAN_LIVEPORTRAIT_PYTHON=./vendor/LivePortrait/.venv/bin/python
DIGITAL_HUMAN_LIVEPORTRAIT_DRIVING=./data/motion/licensed-driver.mp4
```

把你本人制作或已获授权的 driving video 放到 `data/motion/licensed-driver.mp4`，然后显式选择 LivePortrait 运行：

```bash
DIGITAL_HUMAN_MOTION_BACKEND=liveportrait \
DIGITAL_HUMAN_LIVEPORTRAIT_DRIVING=./data/motion/licensed-driver.mp4 \
./scripts/demo_local.sh /path/to/your-authorized-avatar.png "欢迎来到我的频道"
```

LivePortrait 只在头像首次建立时运行并缓存 `base.mp4`；同一头像后续短句只运行 Qwen3-TTS + MuseTalk。没有安装 LivePortrait 时，`static` 会保留可验证的静态头像回退路径。

第一次 TTS 会下载约 1.65GB 的 8-bit 模型。支持的中文预设音色以模型返回为准，常用值包括 `Vivian`、`Serena`、`Uncle_Fu`、`Dylan`、`Eric`。

### 本地说话循环（无需逐字对口型）

卡通头像推荐先测试此模式：LivePortrait 一次生成嘴、眼睛和头部动作，后续只运行真实 Qwen TTS，并循环已有视频。MuseTalk 不参与，不需要启动它的 sidecar。嘴会按驱动素材运动，不跟随音频；自然程度仍取决于驱动素材和头像，缓存不会自动改善表情。

```dotenv
DIGITAL_HUMAN_BACKEND=local
DIGITAL_HUMAN_RENDER_MODE=loop
DIGITAL_HUMAN_MOTION_BACKEND=liveportrait
DIGITAL_HUMAN_LIVEPORTRAIT_DRIVING=./data/motion/licensed-driver.mp4
DIGITAL_HUMAN_LIVEPORTRAIT_DRIVING_MULTIPLIER=1.0
```

驱动视频应由你本人制作或已获授权，正视、轻微眨眼、小幅张嘴通常更适合短说话循环。不要把 LivePortrait 上游示例视频或来源不明的 `.pkl` 放入产品素材。强度越低动作越小，也可能使嘴几乎不动。每个头像的驱动预处理只运行一次，之后会从缓存复用。

运行本地说话循环：

```bash
DIGITAL_HUMAN_RENDER_MODE=loop \
DIGITAL_HUMAN_MOTION_BACKEND=liveportrait \
DIGITAL_HUMAN_LIVEPORTRAIT_DRIVING=./data/motion/licensed-driver.mp4 \
DIGITAL_HUMAN_LIVEPORTRAIT_DRIVING_MULTIPLIER=1.0 \
./scripts/demo_local.sh /path/to/your-authorized-avatar.png "欢迎来到我的频道"
```

演示脚本在 `loop` 模式跳过 MuseTalk 启动。`loop` 强制要求 LivePortrait，不会悄悄降级为静态头像。`/readyz` 会明确返回 `audio_driven: false`；它检查组件是否可用，不代表头像质量或全部模型权重已经验证。

驱动文件内容和动作强度参与头像缓存键。修改配置后重启服务、重新上传头像可建立新动作缓存；旧头像 ID 仍复用旧动作。只有显式配置 `.pkl` 才复用模板，避免替换视频后误用过期的同名模板。

## API

上传并缓存头像：

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/avatars -F image=@/path/to/your-authorized-avatar.png
```

也可以设置 `OPENAI_API_KEY` 后调用 `POST /v1/avatars/generate`。默认使用 `gpt-image-2.5-flare`，模型名可通过环境变量覆盖。OpenAI 图像只在头像创建时调用一次，之后 TTS 和视频均在本地执行。

创建视频：

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/renders \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-001' \
  -d '{"avatar_id":"替换为上传结果","text":"欢迎来到我的频道","voice":"Vivian","language":"Chinese"}'
```

轮询返回的 `status_url`；成功后下载 `result_url`。同一个幂等键与同一请求会返回原任务；同一键配不同请求返回 409。

端点：

- `GET /healthz`：进程和 FFmpeg
- `GET /readyz`：队列 worker 与口型 sidecar
- `POST /v1/avatars`：上传头像，规范化并建立持久缓存
- `POST /v1/avatars/generate`：可选 OpenAI Images 头像生成
- `POST /v1/renders`：加入单并发渲染队列
- `GET /v1/jobs/{job_id}`：查询阶段和错误
- `GET /v1/jobs/{job_id}/result`：下载 MP4
- Swagger UI：`http://127.0.0.1:8000/docs`

## LivePortrait 兼容性

LivePortrait 官方仓库提供 macOS Apple Silicon 的 MPS fallback 路径；Intel Mac 不在支持范围内。当前依赖解析需要 Python 3.11、FFmpeg 和 Hugging Face 权重，且在 24GB 机器上建议单任务运行。其输出是整脸动作，MuseTalk 负责最后的中文嘴型。

## 兼容性与限制

- 官方 MuseTalk 1.5 文档仍要求 CUDA；MPS 路径来自第三方端口。
- 端口公开性能只覆盖 M3 Ultra，不等于 24GB Mac 的保证；本项目采用更保守的单任务与小 batch。
- MuseTalk 会把 24kHz Qwen WAV 内部重采样到 16kHz 提取 Whisper 特征，最终视频仍复用原始 WAV，不需手工预重采样。
- 发布或商业使用前，要分别核对 MuseTalk、Qwen、模型权重和所有依赖的许可证。

## 商用与发布边界

- 根项目采用专有、保留权利的公开查看声明；GitHub 公开可见不等于买家获得了使用或再分发权。付费产品包含项目源码与 skill，须由购买者单独取得书面许可；第三方组件、权重、示例素材与生成结果不在该许可范围内。
- LivePortrait 的代码许可为 MIT，但它使用的 InsightFace 检测模型仅限非商业研究。本仓库的安装脚本要求显式选择研究用途；没有商用可替代 detector，因此本实现的 LivePortrait 全脸动画**不能宣称已商业清权**。
- MuseTalk、Qwen3-TTS/MLX-Audio、VAE、Whisper、face-parser 和其他间接依赖分别有自己的许可。模型权重不随仓库分发；见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [models/README.md](models/README.md)。
- 商业发售前还必须清理人像/驱动素材、解决 face-parser 与 ResNet-18 权重的准确来源和许可、移除 LivePortrait 非商业 InsightFace 权重或取得许可、锁定两个 sidecar 的全部依赖，并在目标 24GB Mac 上实测。

因此当前技术状态是**本地开发 preview**，不是已完整清权的商业模型包或公网 SaaS。

参考：[OpenAI Image generation](https://developers.openai.com/api/docs/guides/image-generation)、[MLX-Audio Qwen3-TTS quickstart](https://github.com/Blaizzy/mlx-audio/blob/main/docs/getting-started/quickstart-python.md)、[MuseTalk upstream](https://github.com/TMElyralab/MuseTalk)、[MuseTalk Mac port](https://github.com/barnent1/musetalk-mac)。
