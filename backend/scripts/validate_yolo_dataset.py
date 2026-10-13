"""Fail fast unless the civic detector dataset is ready for real training."""
import argparse
import hashlib
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'datasets' / 'civic_yolo'
CLASSES = [
    'Road Damage', 'Garbage Overflow', 'Water Leakage', 'Drainage Blockage',
    'Broken Street Light', 'Fallen Tree', 'Electric Pole Damage', 'Illegal Dumping',
    'Flood', 'Fire', 'Traffic Signal', 'Public Property Damage', 'Animal Issue',
    'Medical Emergency',
]
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
SPLITS = ('train', 'val', 'test')


def _validate_label(path):
    seen_classes = set()
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f'{path}:{line_number}: YOLO label needs 5 values')
        class_id = int(parts[0])
        if class_id not in range(len(CLASSES)):
            raise ValueError(f'{path}:{line_number}: invalid class id {class_id}')
        values = [float(value) for value in parts[1:]]
        if any(value < 0 or value > 1 for value in values) or values[2] <= 0 or values[3] <= 0:
            raise ValueError(f'{path}:{line_number}: coordinates must be normalized and box width/height positive')
        seen_classes.add(class_id)
    if not seen_classes:
        raise ValueError(f'{path}: label file has no bounding boxes')
    return seen_classes


def _validate_image(path):
    """Verify that an evidence image is decodable before training starts."""
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except Exception as exc:
        raise ValueError(f'{path}: unreadable image ({exc})') from exc
    if width < 32 or height < 32:
        raise ValueError(f'{path}: image is too small ({width}x{height})')


def validate(minimum_per_class=1):
    errors, hashes = [], {}
    class_images, split_images = defaultdict(set), defaultdict(int)
    class_images_by_split = {split: defaultdict(set) for split in SPLITS}
    for split in SPLITS:
        image_dir, label_dir = DATASET / 'images' / split, DATASET / 'labels' / split
        if not image_dir.is_dir() or not label_dir.is_dir():
            errors.append(f'missing {split} images or labels directory')
            continue
        for image in image_dir.iterdir():
            if image.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                _validate_image(image)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            label = label_dir / f'{image.stem}.txt'
            if not label.is_file():
                errors.append(f'missing label for {image}')
                continue
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in hashes:
                errors.append(f'duplicate image: {image} duplicates {hashes[digest]}')
            hashes[digest] = image
            try:
                classes = _validate_label(label)
            except (ValueError, UnicodeDecodeError) as exc:
                errors.append(str(exc))
                continue
            split_images[split] += 1
            for class_id in classes:
                resolved_image = image.resolve()
                class_images[class_id].add(resolved_image)
                class_images_by_split[split][class_id].add(resolved_image)
    for class_id, class_name in enumerate(CLASSES):
        count = len(class_images[class_id])
        if count < minimum_per_class:
            errors.append(f'{class_name}: {count} labelled images; need at least {minimum_per_class}')
        missing_splits = [split for split in SPLITS if not class_images_by_split[split][class_id]]
        if missing_splits:
            errors.append(f'{class_name}: needs at least one labelled image in each split; missing {", ".join(missing_splits)}')
    if not split_images['train'] or not split_images['val'] or not split_images['test']:
        errors.append('train, val, and test splits must each contain labelled images')
    if errors:
        raise RuntimeError('Civic YOLO dataset is not training-ready:\n- ' + '\n- '.join(errors))
    return {'splits': dict(split_images), 'classes': {CLASSES[key]: len(value) for key, value in class_images.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--minimum-per-class', type=int, default=1)
    args = parser.parse_args()
    print(validate(args.minimum_per_class))
