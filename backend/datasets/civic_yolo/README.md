# Civic YOLOv8 Dataset

This is the only dataset accepted by the production civic detector.  Do not put
COCO weights, unlabelled downloads, or generic object images in this folder.

```
civic_yolo/
  images/{train,val,test}/
  labels/{train,val,test}/
  data.yaml
```

The repository-relative image intake paths are:

- Training images: `backend/datasets/civic_yolo/images/train/`
- Validation images: `backend/datasets/civic_yolo/images/val/`
- Held-out test images: `backend/datasets/civic_yolo/images/test/`
- Matching labels: `backend/datasets/civic_yolo/labels/<split>/<same-image-name>.txt`

Keep category IDs aligned with `data.yaml` and `scripts/validate_yolo_dataset.py`.
The current checkpoint still recognizes only the original eight classes. Add
properly boxed examples for every new class before training and deploying an
expanded checkpoint. Record each external dataset's source, license, and
event/location split in `SOURCES.md`. Do not mix near-duplicate frames across
splits.

Every image must have a same-named `.txt` label file containing YOLO bounding
boxes: `<class> <x_center> <y_center> <width> <height>`, normalized to 0–1.
The class IDs are fixed by `data.yaml`:

| ID | Class |
|---:|---|
| 0 | Road Damage |
| 1 | Garbage Overflow |
| 2 | Water Leakage |
| 3 | Drainage Blockage |
| 4 | Broken Street Light |
| 5 | Fallen Tree |
| 6 | Electric Pole Damage |
| 7 | Illegal Dumping |
| 8 | Flood |
| 9 | Fire |
| 10 | Traffic Signal |
| 11 | Public Property Damage |
| 12 | Animal Issue |
| 13 | Medical Emergency |

External starting points for partial class coverage (import only after checking
the source terms and matching its annotations to this class order):

- Fire/smoke object detection, Public Domain: `https://universe.roboflow.com/firedetection-final/fire-detection-final/dataset/1`
- Flood object detection, CC BY 4.0: `https://universe.roboflow.com/deep-learning-dohjx/flood-cka5z/dataset/1`

These do not cover every civic class and are not included in the training splits.
The flood export currently has no validation or test split, so split it by source
event before use. Add attribution for CC BY data in `SOURCES.md`.

Before training, curate and annotate 500–1000 non-duplicate, sharp images per
class.  Split the images by source/event, not random near-duplicates (for
example, 70% train, 20% validation, 10% test).  Include daylight/night,
different weather, viewpoints, and distances.  The test split must remain
unseen until the final evaluation.

Run the quality gate before training:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\validate_yolo_dataset.py --minimum-per-class 500
```

It checks the three splits, decodable images, matching labels, normalized YOLO
boxes, exact duplicate images, and class coverage.  It deliberately refuses to
train on the placeholder samples currently in this repository.
