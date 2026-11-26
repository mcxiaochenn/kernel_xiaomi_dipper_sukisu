#!/usr/bin/env python3
"""把 Image.gz-dtb + ramdisk 重打包成 dipper boot.img（header v1，无 AVB 签名）。

头参数来自 ramdisk/boot_header.json（从 PixelExperience 官方包 boot.img 精确提取）。
注意：产物未做 AVB 签名，解锁 BL 的设备可直接 fastboot flash boot；
若 vbmeta 报警，另行 `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img`
或刷 AnyKernel3 包（其 patch_vbmeta_flag=auto 会自动处理）。
"""
import argparse
import hashlib
import json
import struct
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernel", required=True, help="Image.gz-dtb 路径")
    ap.add_argument("--ramdisk", required=True, help="ramdisk.cpio.gz 路径")
    ap.add_argument("--header", required=True, help="boot_header.json 路径")
    ap.add_argument("--output", required=True, help="输出 boot.img 路径")
    args = ap.parse_args()

    with open(args.header, encoding="utf-8") as f:
        h = json.load(f)

    with open(args.kernel, "rb") as f:
        kernel = f.read()
    with open(args.ramdisk, "rb") as f:
        ramdisk = f.read()

    page = h["page_size"]
    if page <= 0 or page & (page - 1):
        sys.exit(f"page_size 非法: {page}")

    def pad(b: bytes) -> bytes:
        return b + b"\x00" * ((-len(b)) % page)

    name = h.get("name", "").encode()
    cmdline = h["cmdline"].encode()
    if len(name) > 16:
        sys.exit("name 超过 16 字节")
    if len(cmdline) > 512:
        sys.exit("cmdline 超过 512 字节（v1 头无 extra_cmdline 溢出机制之外的空间）")

    # id 为信息性字段（bootloader 不校验），按 AOSP mkbootimg v1 惯例计算
    id_hash = hashlib.sha1(
        kernel + struct.pack("<I", len(kernel))
        + ramdisk + struct.pack("<I", len(ramdisk))
    ).digest()
    id_field = id_hash + b"\x00" * (32 - len(id_hash))

    header = struct.pack(
        "<8s10I",
        b"ANDROID!",
        len(kernel),
        h["kernel_addr"],
        len(ramdisk),
        h["ramdisk_addr"],
        0,
        h.get("second_addr", 0),
        h["tags_addr"],
        page,
        h["header_version"],
        h["os_version"],
    )
    header += name.ljust(16, b"\x00")
    header += cmdline.ljust(512, b"\x00")
    header += id_field
    header += b"\x00" * 1024  # extra_cmdline
    # 尾部 16 字节按原包复刻（recovery_dtbo_size=0, recovery_dtbo_offset=0, header_size=1648）
    header += struct.pack("<IQI", 0, 0, 1648)

    image = pad(header) + pad(kernel) + pad(ramdisk)
    with open(args.output, "wb") as f:
        f.write(image)

    print(f"==> boot.img 已生成: {args.output}")
    print(f"    kernel  : {len(kernel)} bytes @ 0x{h['kernel_addr']:x}")
    print(f"    ramdisk : {len(ramdisk)} bytes @ 0x{h['ramdisk_addr']:x}")
    print(f"    total   : {len(image)} bytes ({len(image) // page} pages)")
    print(f"    id(sha1): {id_hash.hex()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
