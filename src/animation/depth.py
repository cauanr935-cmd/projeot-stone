from __future__ import annotations

import numpy as np


def estimate_depth(image: np.ndarray) -> tuple[np.ndarray, str]:
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    radial = 1.0 - np.sqrt(((xx - w / 2) / max(w / 2, 1)) ** 2 +
                           ((yy - h / 2) / max(h / 2, 1)) ** 2)
    if image.ndim == 3:
        gray = image.astype(np.float32).mean(axis=2)
        saliency = np.abs(gray - gray.mean())
    else:
        saliency = np.abs(image.astype(np.float32) - float(image.mean()))
    saliency /= max(float(saliency.max()), 1)
    depth = np.clip(.75 * (radial - radial.min()) / max(float(radial.max() - radial.min()), 1e-6)
                    + .25 * saliency, 0, 1)
    return depth.astype(np.float32), "geometric"
