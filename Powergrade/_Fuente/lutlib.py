import numpy as np
import colour

# ---------- Transfer functions ----------
# D-Log2 (DJI Osmo Pocket 4P). Unofficial community decode (AJ3DVFX/dji-dlog2-to-aces-idt),
# 18% grey at code 0.305 (~312/1023), consistent with third-party measurements.
_A = 0.148314799066323
_B = 2.9609352545492250
_C = 0.028961695254132
_G = 0.304985337243402
_S = 0.059439398321493
_K = 16.285770761945304


def dlog2_to_lin(x):
    x = np.asarray(x, dtype=np.float64)
    lin_lo = (x - _A) / _B + _C
    lin_mid = 2.0 ** ((x - _G) / _S + np.log2(0.18))
    lin_hi = 475.0 / (2.0 ** _K - 1.0) * (2.0 ** (_K * x) - 1.0)
    return np.where(x < _A, lin_lo, np.where(x < _G, lin_mid, lin_hi))


def lin_to_dlog2(y):
    y = np.asarray(y, dtype=np.float64)
    lo = (y - _C) * _B + _A
    mid = (np.log2(np.maximum(y, 1e-10)) - np.log2(0.18)) * _S + _G
    hi = np.log2(np.maximum(y * (2.0 ** _K - 1.0) / 475.0 + 1.0, 1e-10)) / _K
    yA = _C  # lin at code _A
    return np.where(y < yA, lo, np.where(y < 0.18, mid, hi))


# Original D-Log (official DJI whitepaper)
def dlog_to_lin(x):
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.14, (x - 0.0929) / 6.025,
                    (10.0 ** (3.89616 * x - 2.27752) - 0.0108) / 0.9892)


# ---------- Gamut matrices to linear Rec.709 ----------
_DG2_TO_AP0 = np.array([[0.6788, 0.2163, 0.1049],
                        [0.0437, 0.9329, 0.0234],
                        [-0.0031, 0.0232, 0.9799]])
_AP0_TO_709 = colour.matrix_RGB_to_RGB(colour.RGB_COLOURSPACES['ACES2065-1'],
                                       colour.RGB_COLOURSPACES['ITU-R BT.709'],
                                       chromatic_adaptation_transform='CAT02')
DG2_TO_709 = _AP0_TO_709 @ _DG2_TO_AP0
DG_TO_709 = colour.matrix_RGB_to_RGB(colour.RGB_COLOURSPACES['DJI D-Gamut'],
                                     colour.RGB_COLOURSPACES['ITU-R BT.709'])
_709_TO_DG2 = np.linalg.inv(DG2_TO_709)


# ---------- Display tone mapping ----------
def highlight_knee(lin709, s0=1.5, k=2.2):
    # Soft-compress stops above grey+s0 (on the max channel, hue preserved) so that
    # ~6.5 stops over grey still roll off instead of clipping.
    lin = np.maximum(lin709, 0.0)
    m = np.max(lin, axis=-1, keepdims=True)
    s = np.log2(np.maximum(m, 1e-8) / 0.18)
    s2 = np.where(s > s0, s0 + k * np.tanh((s - s0) / k), s)
    return lin * 2.0 ** (s2 - s)


def tonemap(lin709, exposure=0.6):
    x = np.maximum(highlight_knee(lin709) * exposure, 0.0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0.0, 1.0)  # display-linear


# ---------- OKLab ----------
_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])
_M1i = np.linalg.inv(_M1)
_M2i = np.linalg.inv(_M2)


def lin_to_oklab(rgb):
    return np.cbrt(np.maximum(rgb, 0.0) @ _M1.T) @ _M2.T


def oklab_to_lin(lab):
    return ((lab @ _M2i.T) ** 3) @ _M1i.T


def _hue_w(h, center, width):
    d = (h - center + 180.0) % 360.0 - 180.0
    return np.exp(-0.5 * (d / width) ** 2), d


DEFAULT = dict(
    exposure=0.6,
    contrast=1.35, pivot=0.52, black=0.0,
    shadow_hue=175.0, shadow_amt=0.022,
    high_hue=75.0, high_amt=0.010,
    sat=1.12,
    blue_center=250.0, blue_width=32.0, blue_shift=-55.0, blue_sat=1.35,
    green_center=138.0, green_width=22.0, green_shift=-14.0, green_sat=0.85, green_dark=0.03,
    warm_center=70.0, warm_width=25.0, warm_sat=1.25,
)


def grade(disp_lin, p=DEFAULT):
    lab = lin_to_oklab(disp_lin)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360.0
    # hue-selective adjustments (weighted by chroma so neutrals stay put)
    t = np.clip(C / 0.05, 0, 1)
    cw = t * t * (3 - 2 * t)
    wb, _ = _hue_w(h, p['blue_center'], p['blue_width'])
    wg, _ = _hue_w(h, p['green_center'], p['green_width'])
    ww, _ = _hue_w(h, p['warm_center'], p['warm_width'])
    h2 = h + cw * (wb * p['blue_shift'] + wg * p['green_shift'])
    C2 = C * (1 + wb * (p['blue_sat'] - 1)) * (1 + wg * (p['green_sat'] - 1)) * (1 + ww * (p['warm_sat'] - 1))
    C2 *= p['sat']
    L2 = L - cw * wg * p['green_dark']
    # contrast S-curve on lightness (sigmoid normalised to keep 0 and 1)
    k = p['contrast'] * 4.0
    def sig(v):
        return 1.0 / (1.0 + np.exp(-k * (v - p['pivot'])))
    s0, s1 = sig(0.0), sig(1.0)
    Lc = (sig(L2) - s0) / (s1 - s0)
    Lc = p['black'] + (1 - p['black']) * Lc
    # contrast boosts perceived chroma too; keep chroma proportional in shadows
    a2 = C2 * np.cos(np.radians(h2))
    b2 = C2 * np.sin(np.radians(h2))
    # split toning
    ws = np.clip((0.6 - Lc) / 0.6, 0, 1) ** 1.3
    wh = np.clip((Lc - 0.5) / 0.5, 0, 1) ** 1.3
    a2 = a2 + ws * p['shadow_amt'] * np.cos(np.radians(p['shadow_hue'])) + wh * p['high_amt'] * np.cos(np.radians(p['high_hue']))
    b2 = b2 + ws * p['shadow_amt'] * np.sin(np.radians(p['shadow_hue'])) + wh * p['high_amt'] * np.sin(np.radians(p['high_hue']))
    # fade tint to zero at pure black/white so ends stay neutral-ish
    out = oklab_to_lin(np.stack([Lc, a2, b2], -1))
    return np.clip(out, 0.0, 1.0)


def encode_709(disp_lin):
    # Rec.709 / BT.1886 display (gamma 2.4)
    return np.clip(disp_lin, 0, 1) ** (1 / 2.4)


def full_pipeline(codes, src='dlog2', p=DEFAULT):
    if src == 'dlog2':
        lin = dlog2_to_lin(codes) @ DG2_TO_709.T
    elif src == 'dlog':
        lin = dlog_to_lin(codes) @ DG_TO_709.T
    else:
        raise ValueError(src)
    return encode_709(grade(tonemap(lin, p['exposure']), p))


def technical_only(codes, src='dlog2', exposure=0.6):
    lin = (dlog2_to_lin(codes) @ DG2_TO_709.T) if src == 'dlog2' else (dlog_to_lin(codes) @ DG_TO_709.T)
    return encode_709(tonemap(lin, exposure))


def write_cube(path, fn, n=33, title='LUT'):
    g = np.linspace(0, 1, n)
    # .cube order: R fastest, then G, then B
    B, G, R = np.meshgrid(g, g, g, indexing='ij')
    rgb = np.stack([R, G, B], -1).reshape(-1, 3)
    out = np.clip(fn(rgb), 0, 1)
    with open(path, 'w') as f:
        f.write(f'TITLE "{title}"\n')
        f.write(f'LUT_3D_SIZE {n}\n')
        f.write('DOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n\n')
        for r, gg, b in out:
            f.write(f'{r:.6f} {gg:.6f} {b:.6f}\n')
    return out


def read_cube(path):
    n = None; data = []
    for line in open(path):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('LUT_3D_SIZE'):
            n = int(s.split()[1]); continue
        if s[0].isalpha():
            continue
        data.append([float(v) for v in s.split()])
    return n, np.array(data).reshape(n, n, n, 3)  # [b][g][r]


def apply_cube(img, n, lut):
    x = np.clip(img, 0, 1) * (n - 1)
    i0 = np.floor(x).astype(int); i0 = np.clip(i0, 0, n - 2); f = x - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    def L(db, dg, dr):
        return lut[b0 + db, g0 + dg, r0 + dr]
    c00 = L(0, 0, 0) * (1 - fr) + L(0, 0, 1) * fr
    c01 = L(0, 1, 0) * (1 - fr) + L(0, 1, 1) * fr
    c10 = L(1, 0, 0) * (1 - fr) + L(1, 0, 1) * fr
    c11 = L(1, 1, 0) * (1 - fr) + L(1, 1, 1) * fr
    c0 = c00 * (1 - fg) + c01 * fg
    c1 = c10 * (1 - fg) + c11 * fg
    return c0 * (1 - fb) + c1 * fb
