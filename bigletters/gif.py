"""A tiny animated GIF writer (no dependencies) and the recorder that feeds it."""


def lzw_encode(data, min_bits=8):
    """GIF flavour of LZW: bytes of palette indices -> compressed bytes"""
    clear, eoi = 1 << min_bits, (1 << min_bits) + 1
    out, cur, nbits = bytearray(), 0, 0
    code_size, next_code, table = min_bits + 1, eoi + 1, {}

    def emit(code):
        nonlocal cur, nbits
        cur |= code << nbits
        nbits += code_size
        while nbits >= 8:
            out.append(cur & 255)
            cur >>= 8
            nbits -= 8

    emit(clear)
    if data:
        prefix = data[0]
        for b in data[1:]:
            key = (prefix << 8) | b
            c = table.get(key)
            if c is not None:
                prefix = c
                continue
            emit(prefix)
            if next_code < 4096:
                table[key] = next_code
                if next_code == (1 << code_size) and code_size < 12:
                    code_size += 1
                next_code += 1
            else:
                emit(clear)
                table.clear()
                code_size, next_code = min_bits + 1, eoi + 1
            prefix = b
        emit(prefix)
    emit(eoi)
    if nbits:
        out.append(cur & 255)
    return bytes(out)


def palette():
    pal = bytearray()
    for r in range(6):
        for g in range(6):
            for b in range(6):
                pal += bytes((r * 51, g * 51, b * 51))
    for i in range(40):
        v = int(i * 255 / 39)
        pal += bytes((v, v, v))
    return bytes(pal)


def write_gif(path, frames, w, h, delay_cs):
    """frames: list of bytes (w*h palette indices)"""
    out = bytearray(b"GIF89a" + w.to_bytes(2, "little") + h.to_bytes(2, "little") + bytes((0xF7, 0, 0)))
    out += palette()
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
    for fr in frames:
        out += b"\x21\xf9\x04\x00" + delay_cs.to_bytes(2, "little") + b"\x00\x00"
        out += b"\x2c\x00\x00\x00\x00" + w.to_bytes(2, "little") + h.to_bytes(2, "little") + b"\x00\x08"
        data = lzw_encode(fr)
        for i in range(0, len(data), 255):
            chunk = data[i:i + 255]
            out += bytes((len(chunk),)) + chunk
        out += b"\x00"
    out += b"\x3b"
    with open(path, "wb") as f:
        f.write(out)


class Recorder:
    SCALE = 2

    def __init__(self, path, seconds, scale=None, every=2, delay_cs=8):
        self.path, self.seconds = path, seconds
        self.scale, self.every, self.delay = scale or self.SCALE, every, delay_cs
        self.frames, self.size, self.cache, self.n = [], None, {}, 0
        self.done = False

    def idx(self, c):
        if c is None:
            c = (0, 0, 0)
        v = self.cache.get(c)
        if v is None:
            v = 36 * ((c[0] * 5 + 127) // 255) + 6 * ((c[1] * 5 + 127) // 255) + (c[2] * 5 + 127) // 255
            self.cache[c] = v
        return v

    def add(self, grid, t):
        if self.done:
            return
        if t > self.seconds:
            self.done = True
            return
        self.n += 1
        if (self.n - 1) % self.every:                # not every frame: ~12 fps is plenty
            return
        S = self.scale
        buf = bytearray()
        for row in grid:
            top, bot = bytearray(), bytearray()
            for a, b in row:
                top += bytes((self.idx(a),)) * S
                bot += bytes((self.idx(b),)) * S
            buf += bytes(top) * S + bytes(bot) * S
        self.size = (len(grid[0]) * S, len(grid) * 2 * S)
        self.frames.append(bytes(buf))

    def save(self):
        if not self.frames:
            return None
        write_gif(self.path, self.frames, self.size[0], self.size[1], self.delay)
        return self.path
