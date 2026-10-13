"""Train an explicitly non-production YOLO experiment on classes with labels.

This script preserves source annotations and never deploys the resulting model.
It requires every selected class in train, validation, and test splits.
"""
import argparse
import json
import shutil
from pathlib import Path

import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'datasets' / 'civic_yolo'
EXPERIMENT = DATASET / 'experiments' / 'six_class'
OUTPUT = ROOT / 'trained_models' / 'experiments' / 'civic_six_class'

parser = argparse.ArgumentParser()
parser.add_argument('--epochs', type=int, default=30)
parser.add_argument('--imgsz', type=int, default=640)
parser.add_argument('--batch', type=int, default=4)
parser.add_argument('--device', default='auto')
args = parser.parse_args()
if not 1 <= args.epochs <= 100:
    parser.error('--epochs must be between 1 and 100')

source_config = yaml.safe_load((DATASET / 'data.yaml').read_text(encoding='utf-8'))
source_names = source_config['names']
if isinstance(source_names, list):
    source_names = dict(enumerate(source_names))
source_names = {int(key): value for key, value in source_names.items()}
selected = [0, 1, 2, 3, 4, 6]
id_map = {source_id: new_id for new_id, source_id in enumerate(selected)}
names = {new_id: source_names[source_id] for source_id, new_id in id_map.items()}

# Build an isolated remapped dataset from the existing labeled files.
for split in ('train', 'val', 'test'):
    image_out = EXPERIMENT / 'images' / split
    label_out = EXPERIMENT / 'labels' / split
    image_out.mkdir(parents=True, exist_ok=True)
    label_out.mkdir(parents=True, exist_ok=True)
    for source_image in (DATASET / 'images' / split).iterdir():
        if source_image.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}:
            continue
        source_label = DATASET / 'labels' / split / f'{source_image.stem}.txt'
        if not source_label.is_file():
            continue
        lines = []
        for line in source_label.read_text(encoding='utf-8').splitlines():
            parts = line.split()
            if parts and int(parts[0]) in id_map:
                parts[0] = str(id_map[int(parts[0])])
                lines.append(' '.join(parts))
        if lines:
            shutil.copy2(source_image, image_out / source_image.name)
            (label_out / f'{source_image.stem}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

for split in ('train', 'val', 'test'):
    counts = {name: 0 for name in names.values()}
    for label in (EXPERIMENT / 'labels' / split).glob('*.txt'):
        for line in label.read_text(encoding='utf-8').splitlines():
            class_id = int(line.split()[0])
            counts[names[class_id]] += 1
    missing = [name for name, count in counts.items() if count == 0]
    if missing:
        raise RuntimeError(f'{split} split is missing selected classes: {missing}')
    print(f'{split} label counts: {counts}')

config = EXPERIMENT / 'data.yaml'
config.write_text(yaml.safe_dump({
    'path': str(EXPERIMENT.resolve()),
    'train': 'images/train', 'val': 'images/val', 'test': 'images/test',
    'names': names,
}, sort_keys=False), encoding='utf-8')

model = YOLO(str(DATASET / 'yolov8s.pt'))
run_dir = OUTPUT / 'run'
model.train(data=str(config), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
            patience=min(10, args.epochs), device=args.device, workers=0,
            project=str(OUTPUT), name='run', exist_ok=True,
            fliplr=0.5, degrees=10.0, scale=0.4, mosaic=0.5,
            hsv_h=0.015, hsv_s=0.3, hsv_v=0.25, plots=True)
best = run_dir / 'weights' / 'best.pt'
if not best.is_file():
    raise RuntimeError(f'Training did not produce a checkpoint: {best}')

evaluation = YOLO(str(best)).val(data=str(config), split='test', conf=0.5,
                                device=args.device, plots=True)
per_class = {name: float(evaluation.box.p[index]) if index < len(evaluation.box.p) else 0.0
             for index, name in enumerate(names.values())}
metrics = {
    'status': 'EXPERIMENTAL_NOT_FOR_PRODUCTION',
    'dataset': str(EXPERIMENT.relative_to(ROOT)),
    'checkpoint': str(best.relative_to(ROOT)),
    'classes': list(names.values()),
    'epochs_requested': args.epochs,
    'test_confidence_threshold': 0.5,
    'test_metrics': {key: float(value) for key, value in evaluation.results_dict.items()},
    'per_class_test_precision': per_class,
    'limitations': 'Very small labeled dataset; metrics are noisy and do not establish reliability on unseen images.',
}
(OUTPUT / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
print(json.dumps(metrics, indent=2))
