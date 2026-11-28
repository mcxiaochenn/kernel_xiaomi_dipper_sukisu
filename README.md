# kernel_xiaomi_dipper_sukisu — miui-20.9.4 分支

为 **MIUI 20.9.4 dev（dipper / 小米 8，Simplicity-Auto 20200904，线刷底包 `dipper_images_V12.5.2.0.QEACNXM`）** 构建集成 [SukiSU](https://sukisu.org/zh/) + SUSFS 的内核（**4.9.186-perf**），编译、打包、发布全部走 GitHub Actions，本地零编译。

本分支对应 boot.img 内核实测身份：`Linux version 4.9.186-perf-g83532fd (gcc 4.9.x 20150123 prerelease) #1 SMP PREEMPT Thu Sep 3 23:26:11 CST 2020`。

- 内核源：[MiCode/Xiaomi_Kernel_OpenSource](https://github.com/MiCode/Xiaomi_Kernel_OpenSource) `dipper-q-oss` 分支（Android Q，基线 `LA.UM.8.3.r1-05800-sdm845.0`，pin 到 `dcfb1676`）
- SukiSU：[SukiSU-Ultra/SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) `builtin` 分支（手动 hooks 路线，适合非 GKI 4.x 内核）
- 工具链：AOSP GCC 4.9 prebuilt（LineageOS 镜像，与 MIUI 原厂构建同代工具链）
- 集成方式：内核源码内置（`CONFIG_KSU=y` + `CONFIG_KSU_SUSFS=y`），不含 KPM

> master 分支是 PixelExperience 14.0（4.9.337）产品线，与本分支是**不同的内核树**，patch 不通用。本分支所有 kernel patch 已针对 `dipper-q-oss` 4.9.186 重新适配并做过 clean-room 应用验证。

## 与 master 的差异

| | master（PE 14.0） | 本分支（miui-20.9.4） |
|---|---|---|
| 内核树 | PE `kernel_xiaomi_sdm845@4.9.337` | MiCode `dipper-q-oss@4.9.186` |
| defconfig | `dipper_defconfig` | `dipper_user_defconfig`（`-perf` 后缀与实机一致） |
| 工具链 | AOSP Clang r487747c | AOSP GCC 4.9 |
| ramdisk/boot 头 | PE 官方包 | Simplicity ROM 包 boot.img 提取 |
| 产品线 | 基础 root + SUSFS 双线 | 仅 SUSFS 线（`build.yml` 在本分支已移除，避免与 master 定时任务重复发布） |
| tag 格式 | `v1.0.x` / `susfs-v1.0.x` | `miui-20.9.4-*` |

## 4.9.186 适配要点（相对 PE 4.9.337 的重新适配）

`patches/susfs-49-v2.4.0.patch`（susfs v2.4.0 内核树侧，源自 [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的 4.9 适配）对本树的 5 处形态差异手动适配后重新生成：

1. `fs/namei.c` — 外部声明块锚点（本树无 `trace/events/namei.h`，改锚到 `mount.h` 之后）
2. `fs/readdir.c` — `verify_dirent_name()` 是 4.9.337 stable backport，本树没有；`filldir`/`filldir64` 的 `struct inode *inode` 声明改为插在 `reclen` 声明之后
3. `fs/notify/fdinfo.c` — `inotify_fdinfo` 本树用 `mark->mask & IN_ALL_EVENTS` + `ignored_mask:%x` 形态（4.9.337 是 `inotify_mark_user_mask()`），spoof 分支输出格式同步适配
4. `fs/proc/cmdline.c` — 本树用 `saved_command_line`（PE 树有 `new_command_line` 定制实现）
5. `security/selinux/avc.c` — `avc_dump_query` 本树是 4 参数老式签名（无 `struct selinux_state *`，4.17+ 才有），spoof 块插入点适配

`patches/ksu-49-compat.patch`（SukiSU 侧）在 PE 线基础上新增 `current_sid()` 兼容 shim（4.9 `objsec.h` 无此 helper，SukiSU `selinux.c` 依赖它做 zygote/init 域判定）。

## 产物与刷入

文件命名（含四要素：设备、内核版本、SukiSU 版本、UTC 时间戳）：

`boot_dipper-<内核版本>-sukisu-susfs-<SukiSU版本>-<UTC时间戳>`

| 产物 | 用法 |
|---|---|
| `*.zip` | AnyKernel3 卡刷包，Recovery 下刷入（推荐，自动处理 vbmeta） |
| `*.img` | 裸镜像，`fastboot flash boot`（救砖用；如 vbmeta 报警，另刷 `vbmeta.img` 或加 `--disable-verification`） |
| `SHA256SUMS` | 校验和 |

刷入前提：Bootloader 已解锁（**保持解锁，不回锁**）+ 刷有本 ROM 包（内核与 ROM 的 ramdisk/vendor 配套，勿跨 ROM 混刷）。

> ROM 包来源：MI_8_DEV-20200904-20.9.4-10.0-933b0367-Simplicity-Auto.zip（其 boot.img 内核为 MIUI 官方 4.9.186-perf，root 由卡刷脚本自动装 Magisk 20.4；本内核产品线以 SukiSU+SUSFS 替代之）

## 仓库结构

```
.github/workflows/build-susfs.yml   # SUSFS 线：构建 + 打包 + 发布（手动触发）
config/ksu-susfs.fragment           # CONFIG_KSU + CONFIG_KSU_SUSFS 全家桶
patches/
  0001..0005-ksu-*-hook.patch       # 4.9 内核手动 hooks（execve/faccessat/stat/sys_reboot/setresuid）
  susfs-49-v2.4.0.patch             # SUSFS v2.4.0 内核树侧补丁（4.9.186 重新适配）
  ksu-49-compat.patch               # SukiSU 侧 4.9 兼容（含 current_sid shim）
ramdisk/
  ramdisk.cpio.gz                   # 从 Simplicity ROM boot.img 提取的 ramdisk
  boot_header.json                  # boot.img 头参数（同上，精确提取）
scripts/
  integrate.sh                      # pin 住的 SukiSU 内核接线（不执行远端 setup.sh）
  repack_boot.py                    # mkbootimg 等价重打包 boot.img
```

## CI 构建流程

1. 拉内核源（MiCode `dipper-q-oss@dcfb1676`）→ 合并 `dipper_user_defconfig` + `config/ksu-susfs.fragment`
2. `scripts/integrate.sh` 克隆 SukiSU 到 `KernelSU/`，symlink `drivers/kernelsu`，接好 Makefile/Kconfig
3. `git apply patches/000*.patch`（5 条手动 hooks）+ `patches/susfs-*.patch`；SukiSU 侧 `git -C KernelSU apply patches/ksu-*.patch`
4. AOSP GCC 4.9 + ccache 编译 `Image.gz-dtb`
5. 打包 AnyKernel3 zip + `repack_boot.py` 重打包 boot.img + SHA256SUMS
6. 触发时带 `release_tag` 则发 Release（tag 一经发布不覆盖）

构建缓存三层：GCC 工具链（`aosp-gcc-4.9-*`）、ccache（`ccache-*-gcc49-*`）、apt archives。

## 手动构建

Actions → **Build and Release (SUSFS / miui-20.9.4)** → Run workflow：

- `ksu_ref`：SukiSU 的 commit/分支/tag，留空用 `builtin`
- `release_tag`：填 `miui-20.9.4-susfs-v1.0.0` 这类 tag 则构建后发 Release；留空只出 artifact

## 已知限制

- boot.img 未做 AVB 签名（解锁 BL 直刷无碍；AnyKernel3 的 `patch_vbmeta_flag=auto` 会顺手处理）
- susfs 上游（kutemeikito/susfs4ksu）无 4.9 分支，4.9 的内核树侧移植属社区适配——本分支 patch 为针对本树的二次适配，SUSFS 功能以实机验证为准
- 本分支无定时任务，SukiSU `builtin` 更新后需手动触发

## 修订记录

- **miui-20.9.4 分支建立**：针对 MiCode `dipper-q-oss` 4.9.186 树重新适配 susfs v2.4.0（5 处形态差异）+ SukiSU `current_sid` 4.9 shim，工具链换 AOSP GCC 4.9，ramdisk/boot 头换 Simplicity ROM 实物提取，clean-room 验证 6 个 patch 全部干净应用
