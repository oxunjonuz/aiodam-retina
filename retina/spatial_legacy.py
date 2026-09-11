"""Historical spatial functions; zero-background and top-eight assumptions retained."""
import numpy as np

def color_histogram(f):
    counts = np.bincount(f.flatten().astype(np.int64), minlength=16)
    return [int(c) for c in counts[:16]]



def major_components(f, max_n=8):
    """Up to max_n non-background components in ABSOLUTE frame pixels."""
    ff = f.astype(np.int64)
    mask = ff != 0
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    H, W = ff.shape
    for yy in range(H):
        for xx in range(W):
            if not mask[yy, xx] or seen[yy, xx]:
                continue
            colour = int(ff[yy, xx])
            stack = [(yy, xx)]
            seen[yy, xx] = True
            cells_list = []
            while stack:
                cy, cx = stack.pop()
                cells_list.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if (0 <= ny < H and 0 <= nx < W and mask[ny, nx]
                                and not seen[ny, nx] and int(ff[ny, nx]) == colour):
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            ys = [c[0] for c in cells_list]
            xs = [c[1] for c in cells_list]
            area = len(cells_list)
            if area >= 2:
                out.append([colour,
                            int(sum(xs) / area),
                            int(sum(ys) / area),
                            max(xs) - min(xs) + 1,
                            max(ys) - min(ys) + 1])
    out.sort(key=lambda c: -(c[3] * c[4]))
    return out[:max_n]



def center_patch(f, radius=6):
    """Fixed 13x13 window at the frame centre (no hero tracking needed)."""
    H, W = f.shape
    cy, cx = H // 2, W // 2
    x0, x1 = cx - radius, cx + radius + 1
    y0, y1 = cy - radius, cy + radius + 1
    patch = np.zeros((2 * radius + 1, 2 * radius + 1), dtype=f.dtype)
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(W, x1), min(H, y1)
    patch[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = f[sy0:sy1, sx0:sx1]
    return [int(v) for v in patch.flatten()]

