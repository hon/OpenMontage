# 渲染引擎选型指南

> 提炼自 `skills/meta/animation-runtime-selector.md` + `skills/core/hyperframes.md`

---

## 决策矩阵

### Remotion（React 组件，数据驱动）

| 适用场景 | 原因 |
|---|---|
| 现有 explainer 场景堆栈（TextCard、StatCard、图表、CaptionOverlay、TalkingHead） | 组件已存在，零成本复用 |
| 逐字字幕 / 卡拉 OK 字幕 | `remotion_caption_burn` 是 Remotion 独有功能 |
| 虚拟人 / 唇形同步 / 主持人 | TalkingHead 组件只存在于 Remotion |
| 数据图表（柱状图、折线图、饼图） | Remotion 内置图表组件 |
| 终端 / CLI 演示 | 已有 `TerminalScene` 组件 |

### HyperFrames（HTML/CSS/GSAP，动效主导）

| 适用场景 | 原因 |
|---|---|
| 动态字体排版（Kinetic Typography） | HTML/GSAP 是天然表达方式 |
| 产品广告 / 发布预告 / 营销标题卡 | CSS/GSAP 匹配设计师思维模式 |
| 网站 → 视频 / UI 驱动视频 | 有专门的 `website-to-video` 工作流 |
| 需要 registry 组件（grain overlay、shader transition 等） | `hyperframes add` 是 HyperFrames 独有的 |
| 节奏同步音乐视频（音频驱动场景切换） | `hyperframes beats` 检测鼓点后按节拍布置帧 |
| 短动效图形（lower-third、数据弹出、logo 开场） | `motion-graphics` 技能全覆盖 |
| SVG 字符动画、骨骼动画 | GSAP 生态更好 |

### FFmpeg

| 适用场景 | 原因 |
|---|---|
| 纯拼接 / 裁剪源片段 | 不需要合成引擎，FFmpeg 直接完成 |

---

## 一句话直觉

> **有数据 + 字幕 + 虚拟人 → Remotion**
> **有动效 + 排版 + 网页素材 → HyperFrames**
> **只有源文件要拼起来 → FFmpeg**

---

## 硬性规则

当 Remotion 和 HyperFrames 同时可用时，agent **必须**：

1. 检查 `video_compose.get_info()["render_engines"]` 确认可用引擎
2. 向用户展示两个选项，附 pros/cons
3. 给出推荐及理由
4. 等待用户批准后才锁定 `render_runtime`
5. 将决策记录到 `decision_log`

禁止无声切换运行时。任何时候更换运行时都必须新建 `render_runtime_selection` 决策记录。

---

## 各 Pipeline 当前适配状态

| Pipeline | HyperFrames 支持 |
|---|---|
| `animation` | ✅ Wave 1 — 动效为主的场景首选 |
| `animated-explainer` | ✅ Wave 1 — HTML/GSAP 原生场景可用；数据图表多的仍默认 Remotion |
| `screen-demo` | ✅ Wave 1 — 合成 UI 可用；终端演示仍用 Remotion TerminalScene |
| `cinematic` | 🔄 Wave 2 |
| `hybrid` | 🔄 Wave 2 |
| `documentary-montage` | 🔄 Wave 2 |
| `talking-head` | ❌ 依赖 TalkingHead 组件同步 |
| `avatar-spokesperson` | ❌ 同上 |
| `clip-factory` | ❌ 依赖 Remotion 字幕功能 |
| `podcast-repurpose` | ❌ 同上 |
| `localization-dub` | ❌ 同上 |
