"""Train and test a civic-problem image classifier from ``backend/datasets``.

Dataset layout: datasets/Road_Damage/*.jpg, datasets/Garbage/*.jpg, etc.
Each label is deterministically split into 80% train, 10% validation and 10%
test. Run after installing optional dependencies:
    pip install tensorflow scikit-learn
    python train_model.py
"""
import json
import os
import random
from pathlib import Path

ROOT = Path(__file__).parent
DATASET_ROOT = ROOT / 'datasets'
MODEL_DIR = ROOT / 'trained_models'
VALID_SUFFIXES = {'.jpg', '.jpeg', '.png'}
EXCLUDED_FOLDERS = {'processed', 'raw'}
MIN_IMAGES_PER_CLASS = 10

def make_split():
    """Create a deterministic, class-balanced split from curated image folders.

    ``raw`` contains archives/source material, not labels, and ``processed``
    contains other task formats. Neither must be passed to the image model.
    Labels are assigned only after a folder is accepted; the previous approach
    left gaps when sparse folders were skipped and caused out-of-range labels.
    """
    classes, train_paths, train_labels, val_paths, val_labels, test_paths, test_labels = [], [], [], [], [], [], []
    skipped = {}
    for folder in sorted(path for path in DATASET_ROOT.iterdir() if path.is_dir() and path.name not in EXCLUDED_FOLDERS):
        images = sorted(path for path in folder.iterdir() if path.suffix.lower() in VALID_SUFFIXES)
        if len(images) < MIN_IMAGES_PER_CLASS:
            skipped[folder.name] = f'{len(images)} images (need at least {MIN_IMAGES_PER_CLASS} for train/validation/test)'
            continue
        label = len(classes)
        random.Random(42 + label).shuffle(images)
        n_train, n_val = int(len(images) * .8), max(1, int(len(images) * .1))
        if len(images) - n_train - n_val < 1: n_train -= 1
        groups = ((images[:n_train], train_paths, train_labels), (images[n_train:n_train + n_val], val_paths, val_labels), (images[n_train + n_val:], test_paths, test_labels))
        for selected, paths, labels in groups:
            paths.extend(map(str, selected)); labels.extend([label] * len(selected))
        classes.append(folder.name.replace('_', ' '))
    return classes, train_paths, train_labels, val_paths, val_labels, test_paths, test_labels, skipped

def dataset(tf, paths, labels, training=False):
    records = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training: records = records.shuffle(len(paths), seed=42)
    def decode(path, label):
        image = tf.io.decode_image(tf.io.read_file(path), channels=3, expand_animations=False)
        image.set_shape([None, None, 3])
        return tf.image.resize(image, (224, 224)), label
    return records.map(decode, num_parallel_calls=tf.data.AUTOTUNE).batch(16).prefetch(tf.data.AUTOTUNE)

def main():
    try: import tensorflow as tf
    except ImportError as exc: raise SystemExit('TensorFlow is required: pip install tensorflow') from exc
    if not DATASET_ROOT.exists(): raise SystemExit('Create backend/datasets and upload labelled images first.')
    classes, train_p, train_y, val_p, val_y, test_p, test_y, skipped = make_split()
    if len(classes) < 2:
        raise SystemExit('At least two labelled folders with 10 images each are required for image training.')
    MODEL_DIR.mkdir(exist_ok=True)
    augment = tf.keras.Sequential([tf.keras.layers.RandomFlip('horizontal'), tf.keras.layers.RandomRotation(.08), tf.keras.layers.RandomContrast(.12)])
    base = tf.keras.applications.EfficientNetB0(include_top=False, weights='imagenet', input_shape=(224, 224, 3)); base.trainable = False
    model = tf.keras.Sequential([augment, tf.keras.applications.efficientnet.preprocess_input, base, tf.keras.layers.GlobalAveragePooling2D(), tf.keras.layers.Dropout(.25), tf.keras.layers.Dense(len(classes), activation='softmax')])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    history = model.fit(dataset(tf, train_p, train_y, True), validation_data=dataset(tf, val_p, val_y), epochs=8)
    loss, accuracy = model.evaluate(dataset(tf, test_p, test_y), verbose=0)
    model.save(MODEL_DIR / 'civic_classifier.keras')
    report = {
        'classes': classes,
        'skippedFolders': skipped,
        'split': {'train': len(train_p), 'validation': len(val_p), 'test': len(test_p)},
        'test': {'loss': float(loss), 'accuracy': float(accuracy)},
        'history': {k: [float(x) for x in v] for k, v in history.history.items()},
    }
    (MODEL_DIR / 'metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (MODEL_DIR / 'classes.json').write_text(json.dumps(classes), encoding='utf-8')
    print(json.dumps({'split': report['split'], 'classes': classes, 'skippedFolders': skipped}), f"test accuracy: {accuracy:.3f}")

if __name__ == '__main__': main()
