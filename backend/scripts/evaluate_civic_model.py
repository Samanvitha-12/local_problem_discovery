"""Evaluate a deployed civic model and reject-image folder after training.

Usage: python scripts/evaluate_civic_model.py --negative-dir datasets/civic_yolo/negative_test
"""
import argparse
import json
import os
from pathlib import Path

# Keep Ultralytics settings in the project, including when run by Flask/CI.
CONFIG_DIR = Path(__file__).resolve().parents[1] / '.ultralytics'
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ['YOLO_CONFIG_DIR'] = str(CONFIG_DIR)
os.environ['MPLCONFIGDIR'] = str(CONFIG_DIR / 'matplotlib')

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'datasets' / 'civic_yolo' / 'data.yaml'
MODEL = ROOT / 'models' / 'best.pt'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}

parser = argparse.ArgumentParser()
parser.add_argument('--negative-dir', type=Path, default=ROOT / 'datasets' / 'civic_yolo' / 'negative_test')
parser.add_argument('--confidence', type=float, default=0.50)
parser.add_argument('--device', default='auto')
args = parser.parse_args()

if not MODEL.is_file():
    raise FileNotFoundError(f'No deployed civic model at {MODEL}. Train first.')

model = YOLO(str(MODEL))
os.chdir(ROOT)
metrics = model.val(data=str(DATA), split='test', conf=args.confidence, device=args.device, plots=True)
negative_results = []
if args.negative_dir.is_dir():
    for image in args.negative_dir.iterdir():
        if image.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        result = model(str(image), conf=args.confidence, verbose=False)[0]
        negative_results.append({'file': image.name, 'detections': len(result.boxes or [])})

summary = {
    'precision': float(metrics.box.mp),
    'recall': float(metrics.box.mr),
    'mAP50': float(metrics.box.map50),
    'mAP50_95': float(metrics.box.map),
    'negative_images': len(negative_results),
    'negative_false_positives': sum(item['detections'] for item in negative_results),
    'negative_details': negative_results,
}
output = ROOT / 'runs' / 'detect' / 'train' / 'evaluation_summary.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
