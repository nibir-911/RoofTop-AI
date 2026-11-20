"""OFFLINE tool (not part of the customer app): generate CANDIDATE plant sprites with a local image model,
cut out the white background, and save them for human review. Nothing here is used by the app until a
reviewer approves it in tools/review_sprites.py.

Usage (Apple Silicon Mac):
    pip install mflux            # MLX image models; check the model licence before commercial use
    python tools/make_sprites.py --plants tomato,marigold,lau --stages mature --seeds 3
Output: data/sprites_review/<plant_id>/<stage>_seed<N>.png (+ .json with prompt/seed/model)

NOTE: the mflux calls follow its documented Python API (ZImageTurbo(...).generate_image(...)).
Check `mflux` docs if the API changed; the cut-out code below works without any model."""
import argparse, json, os, sys
import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import plants as P

STAGE_TEXT = {"planting": "newly planted small seedling, only a few small leaves, young",
              "mid": "growing plant, about three months old, leafy",
              "mature": "fully grown mature plant, healthy, in bloom or fruit where typical"}
TEMPLATE = ("{desc}. {stage}. Single plant in a plain terracotta pot, centred, whole plant and pot visible, "
            "side view at eye level, pure white background, soft even daylight, realistic photograph, no text, no other objects")


def build_prompt(row, stage):
    return TEMPLATE.format(desc=row["render_prompt"], stage=STAGE_TEXT[stage])


def cutout(bgr, tol=18):
    """White-background cut-out -> BGRA. Flood-fills white from all four corners, feathers the edge."""
    h, w = bgr.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    work = bgr.copy()
    for pt in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        cv2.floodFill(work, mask, pt, (0, 0, 0), (tol,) * 3, (tol,) * 3, cv2.FLOODFILL_MASK_ONLY | (255 << 8))
    bg = mask[1:-1, 1:-1] > 0
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.2)
    ys, xs = np.where(alpha > 10)
    if len(xs) == 0:
        raise ValueError("Nothing left after removing the background")
    out = np.dstack([bgr, alpha])
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plants", required=True, help="comma-separated plant ids")
    ap.add_argument("--stages", default="mature")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--size", type=int, default=768)
    ap.add_argument("--steps", type=int, default=9)
    a = ap.parse_args()
    try:
        from mflux.models.z_image import ZImageTurbo
    except ImportError:
        sys.exit("Install the image model first: pip install mflux")
    model = ZImageTurbo(quantize=8)
    df = P.load_plants()
    for pid in a.plants.split(","):
        row = df.loc[pid]
        for stage in a.stages.split(","):
            for seed in range(1, a.seeds + 1):
                prompt = build_prompt(row, stage)
                img = model.generate_image(prompt=prompt, seed=seed, num_inference_steps=a.steps,
                                           width=a.size, height=a.size)
                d = os.path.join(ROOT, "data", "sprites_review", pid)
                os.makedirs(d, exist_ok=True)
                raw = os.path.join(d, f"{stage}_seed{seed}_raw.png")
                img.save(raw)
                try:
                    bgra = cutout(cv2.imread(raw))
                except ValueError as e:
                    print("skip", pid, stage, seed, e)
                    continue
                out = os.path.join(d, f"{stage}_seed{seed}.png")
                cv2.imwrite(out, bgra)
                json.dump({"plant_id": pid, "stage": stage, "seed": seed, "prompt": prompt,
                           "model": "mflux ZImageTurbo q8"}, open(out[:-4] + ".json", "w"), indent=2)
                print("saved", out)


if __name__ == "__main__":
    main()
