# Lantern · TouchDesigner 动作交互实验

基于 TouchDesigner 的 2.5D 侧视角动作游戏：PS5 DualSense 控制小骑士，摄像头识别真人身体和双手动作并驱动 Boss。主要逻辑由 Script CHOP／Python 实现，材质和特效使用 GLSL。

![游戏画面](docs/gameplay.png)

支持奔跑、平滑转身、跳跃／二段跳、闪避、横向／上劈／空中下劈、受击无敌、碰撞伤害和按 Boss 四肢运动方向计算的击退。武器使用模型内的原始网格，仅在攻击时显示；刀光和闪避各使用一张 4×3、12 帧图集。Boss 使用姿态及手部关键点、骨架局部旋转、关节约束和时间平滑。

## 下载与启动

开发与打包版本：Windows，TouchDesigner **2023.11600**。需要支持该版本的显卡和有效 TD 许可；TouchDesigner 本身不包含在仓库里。其他版本未验证。

1. 安装 [Git LFS](https://git-lfs.com/)，然后克隆整个仓库：

   ```powershell
   git lfs install
   git clone https://github.com/ab123333/touchdesigner-lantern.git
   cd touchdesigner-lantern
   git lfs pull
   ```

2. 在 TouchDesigner 中打开仓库根目录的 `Lantern.toe`。保持 `assets` 与工程的相对位置，允许 TD 执行工程内 Python 脚本。
3. USB 连接 DualSense；需要时在 `/project1/knight_game/dualsense_raw` 选择手柄。没有手柄时可用键盘。
4. 在 `/project1/MediaPipe` 选择本机摄像头并授权相机访问。保证光照、手部和关节可见。首次打开可能需要刷新组件；此时游戏仍可使用键盘操作。
5. 游戏窗口会自动打开，也可查看 `/project1/knight_game/OUT_GAME`，或打开 `PLAY` 的 Viewer。

不要直接使用 GitHub 的普通 “Download ZIP” 来获取大文件：它可能只含 Git LFS 指针。如果 Releases 中提供完整资源包，也可下载该 ZIP 并整体解压。

## 操作

| 动作 | DualSense 默认映射 | 键盘 |
| --- | --- | --- |
| 左右移动 | 左摇杆 | A / D |
| 跳跃／二段跳 | × | Z |
| 闪避 | ○ 或 R1 | X |
| 攻击 | □ | C |
| 上劈／空中下劈 | 摇杆上／下 + 攻击 | W / S + C |
| 重置 | — | R |

不同系统的手柄轴和按键编号可能不同；Controls 页可以调整按钮，`Invertattacky` 可以反转手柄上下攻击方向。键盘输入需要 TD／游戏窗口拥有焦点。下劈只在空中触发。

## 仓库内容

```text
Lantern.toe              可直接打开的完整 TD 工程（Git LFS）
assets/models/           小骑士和 Boss 的 FBX 原始模型
assets/vfx/              刀光、闪避的原始序列图集
src/tdmotion/            游戏、动画、骨架重定向的独立 Python 算法
touchdesigner/           Script CHOP 回调与原工程中的实现源码导出
docs/                    结构说明、内嵌资源清单和校验清单
tests/                   与当前游戏有关的算法回归测试
tools/                   TD 冷启动检查和本地资源校验工具
third_party/             第三方许可文本
```

MediaPipe 的网页程序、WASM 和模型位于 `.toe` 的 Virtual File System 内，清单见 `docs/embedded_resources.json`。TD 的标准摄像机／坐标轴几何仍由 TD 安装目录提供；这些标准程序资源无需另行复制。

运行时脚本已内嵌，不要求安装独立 Python、OpenCV 或 Python MediaPipe。算法测试可使用 Python 3.11+：

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
python tools/verify_bundle.py
```

## 修改和排查

源码映射见 `docs/embedded_sources.json`。`touchdesigner/embedded` 是发布工程内实际 DAT／Shader 的导出；只修改外部 `.py` 不会自动覆盖已内嵌的 DAT。修改时应在 TD 对应 DAT 中更新，并另存工程。可复用算法位于 `src/tdmotion`。

启动后 `.runtime/release_check.json` 检查资源位置、贴图尺寸、Shader／脚本错误；`game_health.json` 和 `retarget_health.json` 提供运行诊断。该目录不进入 Git。未连接手柄时的 joystick warning 属于硬件状态；摄像头权限、驱动和 USB 手柄映射需要在使用者机器上配置。

单目摄像头在遮挡、出画和快速运动下可能丢失关节；当前实现使用限角、平滑和短时保持，不能保证动作捕捉与真人完全一致。本仓库是实验性项目，非《空洞骑士》官方项目。

## 资源与权利说明

第三方来源和许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。模型和美术资源保留原权利归属；公开仓库不等于对全部素材授予再分发或商用许可。本次发布未对未确认权属的模型／美术附加通用开源许可。
