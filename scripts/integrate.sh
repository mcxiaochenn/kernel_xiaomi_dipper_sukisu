#!/bin/bash
# 将 SukiSU 内核源码接线进内核树（等价官方 setup.sh 的接线逻辑，但引用 pin 住的版本，不执行远端脚本）
# 用法: integrate.sh <内核源码根目录> <SukiSU-ref>
set -euo pipefail

KERNEL_ROOT="${1:?用法: integrate.sh <内核源码根目录> <SukiSU-ref>}"
KSU_REF="${2:?缺少 SukiSU ref}"
KSU_REPO="${KSU_REPO:-https://github.com/SukiSU-Ultra/SukiSU-Ultra.git}"

cd "$KERNEL_ROOT"
echo "==> 克隆 SukiSU ($KSU_REPO @ $KSU_REF)"
rm -rf KernelSU
# blobless 克隆：拿完整提交历史（Makefile 要用 rev-list --count 计算版本号），工作树只取 kernel/
git clone --filter=blob:none --sparse "$KSU_REPO" KernelSU
git -C KernelSU sparse-checkout set kernel
git -C KernelSU checkout "$KSU_REF"
# 供 kernel/Makefile 的 git rev-list --count main 计算 KSU_VERSION
git -C KernelSU branch -f main origin/main 2>/dev/null || true
echo "    KSU commit: $(git -C KernelSU rev-parse HEAD)"

echo "==> 接线 drivers/kernelsu -> KernelSU/kernel"
ln -sfn "$(realpath --relative-to=drivers KernelSU/kernel)" drivers/kernelsu

echo "==> 修改 drivers/Makefile / drivers/Kconfig"
if ! grep -q "kernelsu" drivers/Makefile; then
    printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> drivers/Makefile
fi
if ! grep -q 'source "drivers/kernelsu/Kconfig"' drivers/Kconfig; then
    sed -i '/endmenu/i\source "drivers/kernelsu/Kconfig"' drivers/Kconfig
fi

echo "==> 集成完成"
