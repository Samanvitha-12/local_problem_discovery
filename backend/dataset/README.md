# Civic YOLOv8 Dataset

This directory is the source of truth for the civic detector. Its class IDs are
fixed by `data.yaml`; never change their order after annotations are created.

1. Put only sharp, non-duplicate images in `images/train`, `images/val`, and
   `images/test`. Split by incident/source (not near-identical photos).
2. Create a same-named YOLO label for every image in the matching `labels`
   directory: `class_id x_center y_center width height`, all coordinates
   normalised from 0 to 1.
3. Collect at least 500 labelled images for each of the eight classes before
   training. Existing files in `backend/datasets/road_damage` and related
   folders are unlabelled source material, not training data.

Validate before training:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\validate_yolo_dataset.py --minimum-per-class 500
```

The validator rejects missing labels, invalid boxes, duplicate images,
unreadable images, and incomplete splits. It is intentionally impossible to
train or deploy a model until this quality gate passes.
