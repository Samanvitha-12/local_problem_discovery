# Civic YOLOv8 model deployment

Place the real trained civic detector at `backend/models/best.pt`.

The application loads this checkpoint during Flask startup and refuses every
image validation request when it is absent or its class names do not map to the
supported civic categories. Do not replace it with a generic COCO checkpoint.

To create the deployment artifact from the labelled YOLO dataset, run from
`backend`:

```powershell
.\venv\Scripts\python.exe .\scripts\train_yolo_civic.py --model yolov8s.pt --epochs 100
```

The training script copies the resulting real `best.pt` into this directory.
