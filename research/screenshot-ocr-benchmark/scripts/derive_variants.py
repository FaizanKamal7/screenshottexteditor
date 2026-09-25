"""Generate compression/resize variants V00–V13 and manifest.jsonl (METHODOLOGY §5).

Reads dataset/renders/{base_id}.png + ground_truth/{base_id}.json and writes
dataset/images/{image_id}.{ext}, dataset/manifest.jsonl and
dataset/validation/variants.json (PILOT_PLAN checks D1–D6).

Run inside the tools image:
    python scripts/derive_variants.py --dataset pilot/dataset
"""

import argparse
import hashlib
import io
import json
import os
import struct

import numpy as np
import PIL
from PIL import Image, features
from skimage.metrics import structural_similarity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (variant, format, ext, save kwargs, downscale, ocr, quality, subsampling label)
VARIANTS = [
    ("V00", "PNG", "png", {}, 1.0, True, None, None),
    ("V01", "WEBP", "webp", {"lossless": True}, 1.0, False, None, None),
    ("V02", "JPEG", "jpg", {"quality": 95}, 1.0, True, 95, "4:2:0"),
    ("V03", "JPEG", "jpg", {"quality": 85}, 1.0, True, 85, "4:2:0"),
    ("V04", "JPEG", "jpg", {"quality": 75}, 1.0, True, 75, "4:2:0"),
    ("V05", "JPEG", "jpg", {"quality": 60}, 1.0, True, 60, "4:2:0"),
    ("V06", "JPEG", "jpg", {"quality": 85, "subsampling": 0}, 1.0, True, 85, "4:4:4"),
    ("V07", "WEBP", "webp", {"quality": 90, "method": 4}, 1.0, True, 90, "4:2:0"),
    ("V08", "WEBP", "webp", {"quality": 75, "method": 4}, 1.0, True, 75, "4:2:0"),
    ("V09", "WEBP", "webp", {"quality": 50, "method": 4}, 1.0, True, 50, "4:2:0"),
    ("V10", "AVIF", "avif", {"quality": 80}, 1.0, True, 80, "4:2:0"),
    ("V11", "AVIF", "avif", {"quality": 60}, 1.0, True, 60, "4:2:0"),
    ("V12", "PNG", "png", {}, 0.5, True, None, None),
    ("V13", "JPEG", "jpg", {"quality": 75}, 0.5, True, 75, "4:2:0"),
]
FAMILIES = {"jpeg_420": ["V02", "V03", "V04", "V05"], "webp": ["V07", "V08", "V09"], "avif": ["V10", "V11"]}

# Scripts and template files whose content defines the generated dataset.
GENERATOR_FILES = ["scripts/render_chromium.py", "scripts/extract.js", "scripts/derive_variants.py",
                   "fonts/fonts.lock.json"]


def generator_sha256() -> str:
    h = hashlib.sha256()
    paths = list(GENERATOR_FILES)
    for dirpath, _, files in os.walk(os.path.join(ROOT, "templates")):
        for name in files:
            paths.append(os.path.relpath(os.path.join(dirpath, name), ROOT).replace(os.sep, "/"))
    for rel in sorted(paths):
        h.update(rel.encode())
        with open(os.path.join(ROOT, rel), "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
    return h.hexdigest()


def encoder_string(fmt: str) -> str:
    codec = {"PNG": "zlib", "JPEG": "jpg", "WEBP": "webp", "AVIF": "avif"}[fmt]
    return f"Pillow {PIL.__version__} / {codec} {features.version(codec)}"


def pixel_sha256(rgb: np.ndarray) -> str:
    return hashlib.sha256(repr(rgb.shape).encode() + rgb.tobytes()).hexdigest()


def jpeg_subsampling(data: bytes) -> str | None:
    """Read component sampling factors from the SOF marker (PILOT D6)."""
    i = 2
    while i < len(data) - 4:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        (length,) = struct.unpack(">H", data[i + 2 : i + 4])
        if marker in (0xC0, 0xC1, 0xC2):
            ncomp = data[i + 9]
            factors = []
            for c in range(ncomp):
                hv = data[i + 10 + c * 3 + 1]
                factors.append((hv >> 4, hv & 0x0F))
            if len(factors) == 3 and factors[1] == factors[2] == (1, 1):
                return {(1, 1): "4:4:4", (2, 1): "4:2:2", (2, 2): "4:2:0"}.get(factors[0], str(factors))
            return str(factors)
        i += 2 + length
    return None


def psnr(a: np.ndarray, b: np.ndarray) -> float | None:
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return None if mse == 0 else round(10 * np.log10(255.0**2 / mse), 4)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=os.path.join(ROOT, "pilot", "dataset"))
    args = parser.parse_args()

    gen_sha = generator_sha256()
    renders_dir = os.path.join(args.dataset, "renders")
    images_dir = os.path.join(args.dataset, "images")
    os.makedirs(images_dir, exist_ok=True)

    manifest = []
    checks = {"D1": [], "D2": [], "D3": [], "D4": [], "D5": [], "D6": []}
    for name in sorted(os.listdir(renders_dir)):
        base_id = name[:-4]
        with open(os.path.join(args.dataset, "ground_truth", f"{base_id}.json"), encoding="utf-8") as f:
            gt = json.load(f)
        with Image.open(os.path.join(renders_dir, name)) as im:
            base = np.asarray(im.convert("RGB")).copy()
        h, w = base.shape[:2]
        base_img = Image.fromarray(base)
        half = base_img.resize((w // 2, h // 2), Image.LANCZOS)

        rows = {}
        for vid, fmt, ext, kwargs, scale, ocr, quality, subs in VARIANTS:
            src = half if scale != 1.0 else base_img
            buf = io.BytesIO()
            src.save(buf, format=fmt, **kwargs)
            data = buf.getvalue()
            image_id = f"{base_id}_{vid}"
            with open(os.path.join(images_dir, f"{image_id}.{ext}"), "wb") as f:
                f.write(data)
            with Image.open(io.BytesIO(data)) as dec:
                decoded = np.asarray(dec.convert("RGB")).copy()

            expected_shape = (h // 2, w // 2, 3) if scale != 1.0 else (h, w, 3)
            checks["D1"].append({"image_id": image_id, "ok": decoded.shape == expected_shape,
                                 "shape": list(decoded.shape)})
            if scale != 1.0:
                compare_to = np.asarray(Image.fromarray(decoded).resize((w, h), Image.LANCZOS))
                p = psnr(base, compare_to)
                s = structural_similarity(base, compare_to, channel_axis=2, data_range=255)
            else:
                p = psnr(base, decoded)
                s = structural_similarity(base, decoded, channel_axis=2, data_range=255)
            actual_subs = jpeg_subsampling(data) if fmt == "JPEG" else None
            if fmt == "JPEG":
                checks["D6"].append({"image_id": image_id, "expected": subs, "actual": actual_subs,
                                     "ok": actual_subs == subs})
            dh, dw = decoded.shape[:2]
            row = {
                "image_id": image_id,
                "file": f"images/{image_id}.{ext}",
                "base_id": base_id,
                "template_id": gt["template_id"],
                "form_factor": gt["form_factor"],
                "source": "chromium",
                "device": None,
                "os": None,
                "browser": gt["browser"],
                "dpr": gt["dpr"],
                "theme": gt["theme"],
                "variant": vid,
                "format": fmt.lower(),
                "quality": quality,
                "chroma_subsampling": actual_subs if fmt == "JPEG" else subs,
                "lossless": fmt == "PNG" or kwargs.get("lossless", False),
                "downscale": scale,
                "width": dw,
                "height": dh,
                "bytes": len(data),
                "bpp": round(len(data) * 8 / (dw * dh), 6),
                "psnr_vs_v00": p,
                "ssim_vs_v00": round(float(s), 6),
                "encoder": encoder_string(fmt),
                "encoder_settings": kwargs,
                "sha256": hashlib.sha256(data).hexdigest(),
                "pixel_sha256": pixel_sha256(decoded),
                "ocr": ocr,
                "license": "CC-BY-4.0",
                "generator_source_sha256": gen_sha,
            }
            checks["D5"].append({"image_id": image_id,
                                 "ok": bool(row["encoder"]) and row["encoder_settings"] is not None})
            rows[vid] = row
            manifest.append(row)

        checks["D2"].append({"base_id": base_id, "ok": rows["V01"]["pixel_sha256"] == rows["V00"]["pixel_sha256"],
                             "v00_equals_render": rows["V00"]["pixel_sha256"] == pixel_sha256(base)})
        for fam, order in FAMILIES.items():
            sizes = [rows[v]["bytes"] for v in order]
            psnrs = [rows[v]["psnr_vs_v00"] for v in order]
            checks["D3"].append({"base_id": base_id, "family": fam, "bytes": sizes,
                                 "ok": all(a >= b for a, b in zip(sizes, sizes[1:]))})
            checks["D4"].append({"base_id": base_id, "family": fam, "psnr": psnrs,
                                 "ok": all(a >= b for a, b in zip(psnrs, psnrs[1:]))})
        print(f"{base_id}: " + " ".join(f"{v}={rows[v]['bytes']}" for v in rows), flush=True)

    with open(os.path.join(args.dataset, "manifest.jsonl"), "w", encoding="utf-8") as f:
        for row in manifest:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {k: {"total": len(v), "failed": [x for x in v if not x["ok"]]} for k, v in checks.items()}
    summary["D2_v00_equals_render"] = all(x["v00_equals_render"] for x in checks["D2"])
    summary["generator_source_sha256"] = gen_sha
    with open(os.path.join(args.dataset, "validation", "variants.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": checks}, f, indent=1)
    for k in ("D1", "D2", "D3", "D4", "D5", "D6"):
        print(f"{k}: {summary[k]['total'] - len(summary[k]['failed'])}/{summary[k]['total']} ok")


if __name__ == "__main__":
    main()
