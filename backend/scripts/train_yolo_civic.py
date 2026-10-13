"""Train and deploy the production civic detector from labelled civic evidence.

Usage: python scripts/train_yolo_civic.py --model yolov8s.pt --epochs 100

The initial ``yolov8s.pt`` weights are used only for transfer learning. The
deployed ``models/best.pt`` is a newly trained 8-class civic checkpoint; COCO
weights are never deployed or used by the Flask validation path.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

# Services and CI users often cannot write to a profile directory.
CONFIG_DIR = Path(__file__).resolve().parents[1] / '.ultralytics'
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ['YOLO_CONFIG_DIR'] = str(CONFIG_DIR)
os.environ['MPLCONFIGDIR'] = str(CONFIG_DIR / 'matplotlib')

from ultralytics import YOLO
from validate_yolo_dataset import CLASSES, validate

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument('--model', default='yolov8s.pt', choices=('yolov8s.pt', 'yolov8m.pt'))
parser.add_argument('--epochs', type=int, default=100)
parser.add_argument('--imgsz', type=int, default=640)
parser.add_argument('--batch', type=int, default=16)
parser.add_argument('--patience', type=int, default=20)
parser.add_argument('--device', default='auto')
parser.add_argument('--minimum-per-class', type=int, default=500,
                    help='Required labelled images per class across all splits.')
parser.add_argument('--minimum-precision', type=float, default=0.85,
                    help='Minimum held-out test precision required for every class before deployment.')
parser.add_argument('--evaluation-confidence', type=float, default=0.50,
                    help='Confidence threshold used for held-out precision evaluation.')
parser.add_argument('--workers', type=int, default=8)
args = parser.parse_args()
if not 0.0 <= args.minimum_precision <= 1.0:
    parser.error('--minimum-precision must be between 0 and 1')
if not 0.0 <= args.evaluation_confidence <= 1.0:
    parser.error('--evaluation-confidence must be between 0 and 1')

data = ROOT / 'datasets' / 'civic_yolo' / 'data.yaml'
# ``data.yaml`` is intentionally portable (``path: .``).  Resolve its relative
# image paths from the dataset folder, independently of the caller's cwd.
os.chdir(data.parent)
summary = validate(args.minimum_per_class)
print(f'Dataset verified: {summary}')
model = YOLO(args.model)
model.train(
    data=str(data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
    patience=args.patience, device=args.device, workers=args.workers,
    project=str(ROOT / 'runs' / 'detect'), name='train', exist_ok=True,
    # Geometric and colour augmentation for lighting, angle and distance variance.
    fliplr=0.5, degrees=10.0, scale=0.5, mosaic=1.0, hsv_h=0.015,
    hsv_s=0.4, hsv_v=0.3,
)
run = ROOT / 'runs' / 'detect' / 'train'
target = ROOT / 'models'
target.mkdir(exist_ok=True)
best = run / 'weights' / 'best.pt'
if not best.exists():
    raise RuntimeError(f'Training completed without best.pt at {best}')
metrics = YOLO(str(best)).val(data=str(data), split='test', conf=args.evaluation_confidence,
                              device=args.device, plots=True)
per_class_precision = {
    name: float(metrics.box.p[index]) if index < len(metrics.box.p) else 0.0
    for index, name in enumerate(CLASSES)
}
summary = {
    'test': {key: float(value) for key, value in metrics.results_dict.items()},
    'evaluation_confidence': args.evaluation_confidence,
    'minimum_per_class_precision': args.minimum_precision,
    'per_class_precision': per_class_precision,
}
(run / 'deployment_metrics.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
under_target = {name: value for name, value in per_class_precision.items() if value < args.minimum_precision}
if under_target:
    raise RuntimeError(
        'Model not deployed: held-out precision is below the configured minimum '
        f'for these classes: {under_target}. Review the per-class metrics and add '
        'independent labeled examples before training again.'
    )
# Copy only after training and the held-out test evaluation complete.  The
# replace is atomic on Windows, so an in-flight Flask request never observes a
# partially written checkpoint.
temporary_target = target / 'best.pt.tmp'
shutil.copy2(best, temporary_target)
os.replace(temporary_target, target / 'best.pt')
print(f'Deployed real civic model: {target / "best.pt"}')
print(f'Metrics: {run / "deployment_metrics.json"}')
print(f'Plots (losses, PR curves, confusion matrix): {run}')
