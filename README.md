# kernel_xiaomi_dipper_sukisu

为 **PixelExperience 14.0（dipper / 小米 8，20240317-0958 官方包）** 持续构建集成 [SukiSU](https://sukisu.org/zh/) 的内核（4.9.337），编译、打包、发布全部走 GitHub Actions，本地零编译。

- 内核源：[PixelExperience-Devices/kernel_xiaomi_sdm845](https://github.com/PixelExperience-Devices/kernel_xiaomi_sdm845) `fourteen` 分支（已归档，pin 到 `d19207cb`）
- SukiSU：[SukiSU-Ultra/SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) `builtin` 分支（手动 hooks 路线，适合非 GKI 4.x 内核）
- 集成方式：内核源码内置（`CONFIG_KSU=y`），两条产品线：**基础 root**（v1.0.x）与 **root + SUSFS**（susfs-v1.0.x），不含 KPM

## 产品线与 tag 区分

| 产品线 | workflow | config | tag 格式 | 内容 |
|---|---|---|---|---|
| 基础 root | `build.yml` | `config/ksu.fragment` | `v1.0.x` / 自动 `sukisu-<shortsha>` | 仅 `CONFIG_KSU=y` |
| root + SUSFS | `build-susfs.yml` | `config/ksu-susfs.fragment` | `susfs-v1.0.x` | SUSFS v2.4.0 全家桶 |

SUSFS 线的内核树侧补丁为 [`patches/susfs-49-v2.4.0.patch`](patches/susfs-49-v2.4.0.patch)：基于 [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的 `susfs_patch_to_4.9.patch`（simonpunk susfs4ksu v2.4.0 的 4.9 适配）针对本树重新适配；KSU 侧由 SukiSU `builtin` 自带的 `susfs_extension.c` 集成。两条线共用构建缓存。

## 产物与刷入

文件命名（含四要素：设备、内核版本、SukiSU 版本、UTC 时间戳）：

- 基础线：`boot_dipper-<内核版本>-sukisu-<SukiSU版本>-<UTC时间戳>`，如 `boot_dipper-4.9.337-sukisu-4bec532d-20261126-2015Z.zip`
- SUSFS 线：`boot_dipper-<内核版本>-sukisu-susfs-<SukiSU版本>-<UTC时间戳>`，如 `boot_dipper-4.9.337-sukisu-susfs-4bec532d-20261127-1200Z.zip`

| 产物 | 用法 |
|---|---|
| `*.zip` | AnyKernel3 卡刷包，Recovery 下刷入（推荐，自动处理 vbmeta） |
| `*.img` | 裸镜像，`fastboot flash boot`（救砖用；如 vbmeta 报警，另刷 `vbmeta.img` 或加 `--disable-verification`） |
| `SHA256SUMS` | 校验和 |

刷入前提：Bootloader 已解锁 + 刷有本 ROM 包（内核与 ROM 的 ramdisk/vendor 配套，勿跨 ROM 混刷）。

> 刷机包来源：[PixelExperience for dipper](https://get.pixelexperience.org/dipper)（本仓库针对 `PixelExperience_dipper-14.0-20240317-0958-OFFICIAL.zip` 构建）

## 仓库结构

```
.github/workflows/build.yml         # 基础线：构建 + 打包 + 发布 + 定时检测 SukiSU 更新
.github/workflows/build-susfs.yml   # SUSFS 线：构建 + 打包 + 发布（手动触发）
config/ksu.fragment                 # 基础线 CONFIG_KSU=y，合入 dipper_defconfig
config/ksu-susfs.fragment           # SUSFS 线 CONFIG_KSU_SUSFS 全家桶
patches/                            # 4.9 内核手动 hooks 补丁（execve/faccessat/stat/sys_reboot）
  susfs-49-v2.4.0.patch             # SUSFS v2.4.0 内核树侧补丁（4.9 适配，仅 SUSFS 线应用）
ramdisk/
  ramdisk.cpio.gz                   # 从官方包 boot.img 提取的 ramdisk
  boot_header.json                  # boot.img 头参数（从官方包 boot.img 精确提取）
scripts/
  integrate.sh                      # pin 住的 SukiSU 内核接线（不执行远端 setup.sh）
  repack_boot.py                    # mkbootimg 等价重打包 boot.img（复刻头字节，已比对验证）
```

## CI 构建流程

1. 拉内核源（pin commit）→ 合并 `dipper_defconfig` + `config/ksu.fragment`（SUSFS 线用 `ksu-susfs.fragment`）
2. `scripts/integrate.sh` 克隆 pin 住的 SukiSU 到 `KernelSU/`，symlink `drivers/kernelsu`，接好 Makefile/Kconfig
3. `git apply patches/000*.patch`（4 条手动 hooks）；SUSFS 线再加 `patches/susfs-*.patch`
4. AOSP Clang（默认 r487747c）+ ccache 编译 `Image.gz-dtb`
5. 打包 AnyKernel3 zip + `repack_boot.py` 重打包 boot.img + SHA256SUMS
6. 手动触发带 `release_tag` 时发 Release（tag 一经发布不覆盖）；基础线每日定时检测 SukiSU `builtin` 新 commit，有则自动构建并以 `sukisu-<shortsha>` 发布

### 构建缓存（三层）

| 缓存 | key | 效果 |
|---|---|---|
| AOSP Clang | `aosp-clang-<version>` | 跳过 ~1GB 工具链下载 |
| ccache | `ccache-<os>-<clang>…`（带 restore-keys 前缀回退） | 增量编译，调试补丁时大幅提速 |
| apt archives | `apt-v1-<os>` | 跳过依赖下载 |

冷构建与热构建耗时、ccache 命中率见每次 run 的 job summary。实测（v1.0.0 首发两轮，GitHub Actions 4 核）：

| | 编译耗时（make） | job 总时长 | 备注 |
|---|---|---|---|
| 冷构建 | 620s | 11m53s | ccache 部分积累（319MB） |
| 热构建 | **424s** | **8m37s** | 全量 ccache（~1.2GB） |

补丁调试时每轮只重编 SukiSU 相关对象，热构建预计可压到分钟级。

## 手动构建

基础线：Actions → **Build and Release** → Run workflow：

- `ksu_ref`：SukiSU 的 commit/分支/tag，留空用 `builtin`
- `clang_version`：默认 `r487747c`
- `release_tag`：填 `v1.0.0` 这类 tag 则构建后发 Release；留空只出 artifact
- `allow_rebuild`：false 时同 ref 已发布过就跳过

SUSFS 线：Actions → **Build and Release (SUSFS)** → Run workflow，参数同上，`release_tag` 填 `susfs-v1.0.0` 这类格式。SUSFS 线无定时任务，全部手动触发。

## 已知限制

- boot.img 未做 AVB 签名（原包 vbmeta flags=0x0，解锁 BL 直刷无碍；AnyKernel3 的 `patch_vbmeta_flag=auto` 会顺手处理）
- 本内核 ThinLTO 开启，SukiSU 手动 hooks 在 LTO 下的裁剪风险按官方文档对策处理；若实机 hook 失效见 `patches/` 里补丁的回退路线
- 内核源仓库已归档，上游不会再更新——这正是本仓库存在的意义

## 修订记录

- **susfs-v1.0.0**：SUSFS 线建成——SUSFS v2.4.0 内核树侧补丁适配本树（4 处 4.9 形态差异手动适配：`vfs_getattr_nosec` 老式两参签名、`avc_dump_query` 带 `selinux_state` 形态、`cmdline.c` PE 定制实现、`task_mmu.c` 干净 mainline 形态），新增 `build-susfs.yml` 独立 CI 流，tag 以 `susfs-` 前缀区分
- **v1.0.1**：修复 AnyKernel3 刷入报错 `Unable to determine partition`——新版 ak3-core.sh 只认大写变量 `BLOCK`/`IS_SLOT_DEVICE`，v1.0.0 按老配方写的 `block=auto` 被忽略导致 `$BLOCK` 为空；产物命名加上内核版本、SukiSU 版本、UTC 时间戳
- **v1.0.0**：首个构建，boot.img 实机验收通过（SukiSU Manager Working）

## 证据与调研

本仓库的可行性调研报告见 [_rom_research/REPORT-sukisu-dipper.md](../_rom_research/REPORT-sukisu-dipper.md)（包内实测 + 先例核对）。
