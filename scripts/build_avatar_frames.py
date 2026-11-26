"""Build the lip-sync and blink overlays from the existing avatar artwork.

The avatar itself is unchanged: mouth shapes are in-betweens of the idle and
speaking portraits, and the blink is the idle portrait's own eyelid stretched
over the eye. Re-run this if either portrait changes.

    pip install opencv-python-headless numpy
    python scripts/build_avatar_frames.py
"""

from pathlib import Path

import cv2
import numpy as np

AVATARS = Path(__file__).resolve().parents[1] / "frontend" / "public" / "avatars"
# Boxes are (x, y, width, height) in the 1024x1536 portrait. Keep in step with AvatarStage.tsx.
MOUTH = (400, 520, 240, 150)
BLINK = (350, 365, 310, 90)
# Eye outlines: left corner, right corner, upper lid height, lower lid height.
EYES = [((366, 421), (458, 418), 398, 436), ((552, 408), (644, 397), 380, 419)]


def feathered(shape, centre, axes, blur):
    mask = np.zeros(shape, np.float32)
    cv2.ellipse(mask, centre, axes, 0, 0, 360, 1.0, -1)
    return cv2.GaussianBlur(mask, (0, 0), blur)


def save(path, bgr, alpha):
    rgba = np.dstack([bgr, np.clip(alpha * 255, 0, 255).astype(np.uint8)])
    cv2.imwrite(str(path), rgba, [cv2.IMWRITE_WEBP_QUALITY, 95])


def align(idle, speaking):
    """Shift the speaking portrait so its nose and cheeks sit on the idle ones."""
    gray = lambda image: cv2.cvtColor(image[430:540, 420:640], cv2.COLOR_BGR2GRAY).astype(np.float32)
    (dx, dy), _ = cv2.phaseCorrelate(gray(idle), gray(speaking))
    matrix = np.float32([[1, 0, -dx], [0, 1, -dy]])
    return cv2.warpAffine(speaking, matrix, (idle.shape[1], idle.shape[0]), borderMode=cv2.BORDER_REFLECT)


def mouth_frames(idle, speaking):
    x, y, w, h = MOUTH
    a, b = idle[y:y + h, x:x + w], speaking[y:y + h, x:x + w]
    ga, gb = (cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in (a, b))
    forward = cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 4, 25, 5, 7, 1.5, 0)
    backward = cv2.calcOpticalFlowFarneback(gb, ga, None, 0.5, 4, 25, 5, 7, 1.5, 0)
    grid = np.dstack(np.meshgrid(np.arange(w), np.arange(h))).astype(np.float32)
    alpha = feathered((h, w), (w // 2, h // 2 + 2), (90, 52), 9)
    for level, amount in enumerate((0.34, 0.67, 1.0), start=1):
        from_idle = cv2.remap(a, grid - forward * amount, None, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        from_open = cv2.remap(b, grid - backward * (1 - amount), None, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        # Lean on the open portrait as the mouth opens so teeth appear cleanly instead of ghosting.
        weight = float(np.clip((amount - 0.2) / 0.6, 0, 1))
        frame = cv2.addWeighted(from_idle, 1 - weight, from_open, weight, 0)
        save(AVATARS / f"mouth-{level}.webp", frame, alpha)


def blink_frame(idle):
    closed = idle.astype(np.float32).copy()
    alpha = np.zeros(idle.shape[:2], np.float32)
    for (x0, y0), (x1, y1), top, bottom in EYES:
        xs = np.arange(x0 - 4, x1 + 5)
        t = np.clip((xs - x0) / (x1 - x0), 0, 1)
        bulge = np.sin(np.pi * t) ** 0.75
        base = y0 + (y1 - y0) * t
        centre = y0 + (y1 - y0) * 0.5
        upper = base - bulge * (centre - top) - 5
        lower = base + bulge * (bottom - centre) + 3
        for column, u, lo, curve in zip(xs, upper, lower, bulge):
            u, lo = int(round(u)), int(round(lo))
            # Eyelid skin: stretch the strip just above the eye down over it.
            source = idle[u - 9:u - 1, column].astype(np.float32).reshape(-1, 1, 3)
            closed[u:lo + 1, column] = cv2.resize(source, (1, lo - u + 1), interpolation=cv2.INTER_LINEAR)[:, 0]
            alpha[u:lo + 1, column] = 1.0
            lash = int(round(u + (lo - u) * (0.55 + 0.2 * curve)))
            closed[lash:lash + 3, column] = closed[lash:lash + 3, column] * 0.38
    closed = closed.astype(np.uint8)
    closed = np.where(cv2.GaussianBlur(alpha, (0, 0), 1)[..., None] > 0, cv2.GaussianBlur(closed, (3, 3), 0.8), closed)
    alpha = np.clip(cv2.GaussianBlur(alpha, (0, 0), 1.8) * 1.25, 0, 1)
    x, y, w, h = BLINK
    save(AVATARS / "blink.webp", closed[y:y + h, x:x + w], alpha[y:y + h, x:x + w])


if __name__ == "__main__":
    idle = cv2.imread(str(AVATARS / "university-guide-v1.png"))
    speaking = cv2.imread(str(AVATARS / "university-guide-speaking-v1.png"))
    mouth_frames(idle, align(idle, speaking))
    blink_frame(idle)
