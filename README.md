# kernel_xiaomi_dipper_sukisu

为 **PixelExperience 14.0（dipper / 小米 8，20240317-0958 官方包）** 持续构建集成 [SukiSU](https://sukisu.org/zh/) 的内核（4.9.337），编译、打包、发布全部走 GitHub Actions，本地零编译。

- 内核源：[PixelExperience-Devices/kernel_xiaomi_sdm845](https://github.com/PixelExperience-Devices/kernel_xiaomi_sdm845) `fourteen` 分支（已归档，pin 到 `d19207cb`）
- SukiSU：[SukiSU-Ultra/SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) `builtin` 分支（手动 hooks 路线，适合非 GKI 4.x 内核）
- 集成方式：内核源码内置（`CONFIG_KSU=y`），首版仅基础 root，不含 SUSFS / KPM

## 产物与刷入

| 产物 | 用法 |
|---|---|
| `boot.zip` | AnyKernel3 卡刷包，Recovery 下刷入（推荐，自动处理 vbmeta） |
| `boot.img` | 裸镜像，`fastboot flash boot boot.img`（救砖用；如 vbmeta 报警，另刷 `vbmeta.img` 或加 `--disable-verification`） |
| `SHA256SUMS` | 校验和 |

刷入前提：Bootloader 已解锁 + 刷有本 ROM 包（内核与 ROM 的 ramdisk/vendor 配套，勿跨 ROM 混刷）。

> 刷机包来源：[PixelExperience for dipper](https://get.pixelexperience.org/dipper)（本仓库针对 `PixelExperience_dipper-14.0-20240317-0958-OFFICIAL.zip` 构建）

## 仓库结构

```
.github/workflows/build.yml   # 构建 + 打包 + 发布 + 定时检测 SukiSU 更新
config/ksu.fragment           # CONFIG_KSU=y 等，合入 dipper_defconfig
patches/                      # 4.9 内核手动 hooks 补丁（execve/faccessat/stat/sys_reboot）
ramdisk/
  ramdisk.cpio.gz             # 从官方包 boot.img 提取的 ramdisk
  boot_header.json            # boot.img 头参数（从官方包 boot.img 精确提取）
scripts/
  integrate.sh                # pin 住的 SukiSU 内核接线（不执行远端 setup.sh）
  repack_boot.py              # mkbootimg 等价重打包 boot.img（复刻头字节，已比对验证）
```

## CI 构建流程

1. 拉内核源（pin commit）→ 合并 `dipper_defconfig` + `config/ksu.fragment`
2. `scripts/integrate.sh` 克隆 pin 住的 SukiSU 到 `KernelSU/`，symlink `drivers/kernelsu`，接好 Makefile/Kconfig
3. `git apply patches/*.patch`（4 条手动 hooks）
4. AOSP Clang（默认 r487747c）+ ccache 编译 `Image.gz-dtb`
5. 打包 AnyKernel3 zip + `repack_boot.py` 重打包 boot.img + SHA256SUMS
6. 手动触发带 `release_tag` 时发 Release（tag 一经发布不覆盖）；每日定时检测 SukiSU `builtin` 新 commit，有则自动构建并以 `sukisu-<shortsha>` 发布

### 构建缓存（三层）

| 缓存 | key | 效果 |
|---|---|---|
| AOSP Clang | `aosp-clang-<version>` | 跳过 ~1GB 工具链下载 |
| ccache | `ccache-<os>-<clang>…`（带 restore-keys 前缀回退） | 增量编译，调试补丁时大幅提速 |
| apt archives | `apt-v1-<os>` | 跳过依赖下载 |

冷构建与热构建耗时、ccache 命中率见每次 run 的 job summary。

## 手动构建

Actions → **Build and Release** → Run workflow：

- `ksu_ref`：SukiSU 的 commit/分支/tag，留空用 `builtin`
- `clang_version`：默认 `r487747c`
- `release_tag`：填 `v1.0.0` 这类 tag 则构建后发 Release；留空只出 artifact
- `allow_rebuild`：false 时同 ref 已发布过就跳过

## 已知限制

- boot.img 未做 AVB 签名（原包 vbmeta flags=0x0，解锁 BL 直刷无碍；AnyKernel3 的 `patch_vbmeta_flag=auto` 会顺手处理）
- 本内核 ThinLTO 开启，SukiSU 手动 hooks 在 LTO 下的裁剪风险按官方文档对策处理；若实机 hook 失效见 `patches/` 里补丁的回退路线
- 内核源仓库已归档，上游不会再更新——这正是本仓库存在的意义

## 证据与调研

本仓库的可行性调研报告见 [_rom_research/REPORT-sukisu-dipper.md](../_rom_research/REPORT-sukisu-dipper.md)（包内实测 + 先例核对）。
