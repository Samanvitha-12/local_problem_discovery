"""Build the local YOLO dataset from the repository's class-organised images.

The source folders contain one civic issue per image.  This script turns that
class label into a coarse, full-frame YOLO box and makes deterministic
train/validation/test splits.  Review or replace these boxes in an annotation
tool before a production rollout: full-frame boxes are suitable for bootstrapping
the detector, not for measuring small-object localisation accuracy.

Run: python scripts/create_civic_yolo_dataset.py --reset
"""
import argparse
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / 'datasets'
TARGET_ROOT = SOURCE_ROOT / 'civic_yolo'
CLASSES = {
    'road_damage': 0, 'garbage': 1, 'water_leakage': 2, 'drainage': 3,
    'street_light': 4, 'tree_fallen': 5, 'electricity': 6,
    'illegal_dumping': 7,
}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def split_for(path: Path) -> str:
    # A stable hash gives repeatable splits and avoids manually managing files.
    value = int(hashlib.sha256(path.read_bytes()).hexdigest(), 16) % 10
    return 'test' if value == 0 else ('val' if value in (1, 2) else 'train')


def create(reset: bool = False):
    if reset:
        for group in ('images', 'labels'):
            for split in ('train', 'val', 'test'):
                folder = TARGET_ROOT / group / split
                if folder.exists():
                    shutil.rmtree(folder)
    counts = {split: 0 for split in ('train', 'val', 'test')}
    class_counts = {name: 0 for name in CLASSES}
    seen_hashes = set()
    for source_name, class_id in CLASSES.items():
        source = SOURCE_ROOT / source_name
        files = sorted(path for path in source.glob('*') if path.suffix.lower() in IMAGE_EXTENSIONS)
        for index, image in enumerate(files):
            content_hash = hashlib.sha256(image.read_bytes()).hexdigest()
            if content_hash in seen_hashes:
                # A source may be present under two broad categories.  Do not
                # train contradictory labels for exactly the same photo.
                continue
            seen_hashes.add(content_hash)
            split = split_for(image)
            # Guarantee that the scarce two-image class is represented in both
            # validation and test; the other classes remain hash-split.
            if source_name == 'tree_fallen':
                split = ('val', 'test')[index % 2]
            stem = f'{source_name}_{index:04d}'
            image_folder = TARGET_ROOT / 'images' / split
            label_folder = TARGET_ROOT / 'labels' / split
            image_folder.mkdir(parents=True, exist_ok=True)
            label_folder.mkdir(parents=True, exist_ok=True)
            destination = image_folder / f'{stem}{image.suffix.lower()}'
            shutil.copy2(image, destination)
            # YOLO: class x_center y_center width height.  Source images are
            # category-labelled; this full-frame bootstrap box is explicit and
            # can be refined later with CVAT/Label Studio annotations.
            (label_folder / f'{stem}.txt').write_text(f'{class_id} 0.5 0.5 1.0 1.0\n', encoding='utf-8')
            counts[split] += 1
            class_counts[source_name] += 1
    if not all(counts.values()):
        raise RuntimeError(f'Could not create all splits: {counts}')
    return {'splits': counts, 'classes': class_counts, 'target': str(TARGET_ROOT)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='Replace generated image and label split folders.')
    options = parser.parse_args()
    print(create(reset=options.reset))
