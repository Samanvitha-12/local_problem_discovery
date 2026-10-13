# Negative validation images

Place held-out selfies, dogs, cars, food and ordinary scenery here. These files
must never be used as positive civic training images. After training, run:

```powershell
.\venv\Scripts\python.exe scripts\evaluate_civic_model.py
```

The evaluation report records every false positive in
`runs/detect/train/evaluation_summary.json`.
