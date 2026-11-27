import struct, sys, zlib

def extract_kernel(img_path, out_path):
    with open(img_path, 'rb') as f:
        data = f.read()
    assert data[:8] == b'ANDROID!'
    kernel_size = struct.unpack('<I', data[8:12])[0]
    page_size = struct.unpack('<I', data[36:40])[0]
    off = page_size
    kdata = data[off:off+kernel_size]
    with open(out_path, 'wb') as f:
        f.write(kdata)
    print(f'extracted kernel: {kernel_size} bytes -> {out_path}')

extract_kernel(sys.argv[1], sys.argv[2])
