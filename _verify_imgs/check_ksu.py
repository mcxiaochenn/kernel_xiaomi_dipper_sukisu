import struct, sys, zlib, re

def analyze(path):
    with open(path, 'rb') as f:
        data = f.read()
    magic = data[:8]
    assert magic == b'ANDROID!', f'{path}: bad magic {magic!r}'
    kernel_size = struct.unpack('<I', data[8:12])[0]
    page_size = struct.unpack('<I', data[36:40])[0]
    print(f'{path}: kernel_size={kernel_size} page_size={page_size}')
    off = page_size  # header v1: kernel follows first page
    kdata = data[off:off+kernel_size]
    # Image.gz-dtb: gzip stream first
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    img = d.decompress(kdata) + d.flush()
    print(f'  decompressed Image size: {len(img)}')
    hits = {}
    for pat in [b'KernelSU', b'kernelsu', b'sukisu', b'SukiSU', b'ksu_handle_sys_reboot',
                b'ksu_supercall', b'KSU_VERSION', b'on_post_fs_data', b'ksu_is_safe_mode',
                b'susfs', b'SUSFS']:
        n = img.count(pat)
        if n:
            hits[pat.decode()] = n
    print(f'  symbol hits: {hits}')
    return hits

for p in sys.argv[1:]:
    analyze(p)
    print()
