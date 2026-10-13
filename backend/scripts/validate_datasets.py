import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPLAINT_DIRS = [
    ROOT / 'datasets' / 'complaints',
    ROOT / 'datasets' / 'processed' / 'text' / 'complaints',
]
PRIORITY_RULES_PATH = ROOT / 'datasets' / 'priority' / 'india_priority_rules.json'
EMERGENCY_PATH = ROOT / 'datasets' / 'emergency' / 'india_emergency_numbers.json'
VALID_PRIORITIES = {'Critical', 'High', 'Medium', 'Low'}
CATEGORY_MAP = {
    'road_damage': 'Road Damage',
    'garbage': 'Garbage',
    'street_light': 'Street Light',
    'water_leakage': 'Water Leakage',
    'drainage': 'Drainage',
    'electricity': 'Electricity',
    'tree_fallen': 'Tree Fallen',
    'flood': 'Flood',
    'illegal_dumping': 'Illegal Dumping',
    'traffic_signal': 'Traffic Signal',
    'fire': 'Fire',
    'medical_emergency': 'Medical Emergency',
    'animal_issue': 'Animal Issue',
    'public_property_damage': 'Public Property Damage',
    'road damage': 'Road Damage',
    'street light': 'Street Light',
    'water leakage': 'Water Leakage',
    'tree fallen': 'Tree Fallen',
    'illegal dumping': 'Illegal Dumping',
    'traffic signal': 'Traffic Signal',
}
VALID_CATEGORIES = set(CATEGORY_MAP.values())


def normalize_category(raw_value):
    if not raw_value:
        return ''
    text = str(raw_value).strip().lower().replace(' ', '_')
    return CATEGORY_MAP.get(text, str(raw_value).strip())


def normalize_priority(raw_value, raw_priority_label=None, severity=None):
    candidate = (raw_value or '').strip()
    if candidate:
        candidate = candidate.capitalize()
        if candidate in VALID_PRIORITIES:
            return candidate
    if raw_priority_label:
        mapped = str(raw_priority_label).strip().lower()
        mapping = {'critical': 'Critical', 'high': 'High', 'medium': 'Medium', 'low': 'Low'}
        if mapped in mapping:
            return mapping[mapped]
    if severity:
        mapped = str(severity).strip().lower()
        mapping = {'critical': 'Critical', 'high': 'High', 'medium': 'Medium', 'low': 'Low'}
        if mapped in mapping:
            return mapping[mapped]
    return 'Medium'


def _load_complaint_files():
    files = []
    for directory in COMPLAINT_DIRS:
        if directory.exists():
            files.extend(sorted(directory.glob('*.csv')))
    seen = {}
    for path in files:
        seen[path.resolve()] = path
    return list(seen.values())


def validate_complaint_datasets():
    complaint_files = _load_complaint_files()
    if not complaint_files:
        raise RuntimeError('No complaint CSV files were found in the configured dataset folders.')

    valid_rows = []
    errors = []
    for csv_path in complaint_files:
        with csv_path.open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                errors.append(f'{csv_path.name}: missing headers')
                continue
            if 'complaint_text' not in reader.fieldnames:
                errors.append(f'{csv_path.name}: missing complaint_text column')
                continue
            if 'category' not in reader.fieldnames and 'category' not in set(reader.fieldnames):
                errors.append(f'{csv_path.name}: missing category column')
                continue
            for row_number, row in enumerate(reader, start=2):
                text = (row.get('complaint_text') or '').strip()
                if not text:
                    errors.append(f'{csv_path.name}: row {row_number} is missing complaint_text')
                    continue
                category = normalize_category(row.get('category') or '')
                if category not in VALID_CATEGORIES:
                    errors.append(f'{csv_path.name}: row {row_number} has unsupported category {row.get("category")!r}')
                    continue
                priority = normalize_priority(
                    row.get('priority') or '',
                    row.get('priority_label') or '',
                    row.get('severity') or '',
                )
                if priority not in VALID_PRIORITIES:
                    errors.append(f'{csv_path.name}: row {row_number} has unsupported priority {row.get("priority")!r}')
                    continue
                valid_rows.append({'complaint_text': text, 'category': category, 'priority': priority})

    if errors:
        raise RuntimeError('Complaint dataset validation failed:\n- ' + '\n- '.join(errors))
    if len(valid_rows) < 20:
        raise RuntimeError(f'Not enough valid complaint rows for training: {len(valid_rows)}')

    return complaint_files, valid_rows


def validate_priority_rules():
    if not PRIORITY_RULES_PATH.exists():
        raise RuntimeError(f'Priority rules file missing: {PRIORITY_RULES_PATH}')
    with PRIORITY_RULES_PATH.open('r', encoding='utf-8') as handle:
        rules = json.load(handle)
    if not isinstance(rules, dict):
        raise RuntimeError('Priority rules file must contain a JSON object keyed by priority level.')
    for priority in VALID_PRIORITIES:
        entries = rules.get(priority, [])
        if not isinstance(entries, list) or not entries:
            raise RuntimeError(f'Priority rules missing entries for {priority}')
        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise RuntimeError(f'Priority rules entry {idx} for {priority} must be an object.')
            categories = entry.get('categories')
            keywords = entry.get('keywords')
            reason = entry.get('reason')
            if not isinstance(categories, list) or not categories:
                raise RuntimeError(f'Priority rules entry {idx} for {priority} is missing categories.')
            if not isinstance(keywords, list) or not keywords:
                raise RuntimeError(f'Priority rules entry {idx} for {priority} is missing keywords.')
            if not isinstance(reason, str) or not reason.strip():
                raise RuntimeError(f'Priority rules entry {idx} for {priority} is missing a reason.')


def validate_emergency_dataset():
    if not EMERGENCY_PATH.exists():
        raise RuntimeError(f'Emergency dataset file missing: {EMERGENCY_PATH}')
    with EMERGENCY_PATH.open('r', encoding='utf-8') as handle:
        contacts = json.load(handle)
    if not isinstance(contacts, list) or not contacts:
        raise RuntimeError('Emergency dataset must contain a non-empty list of contacts.')
    for index, contact in enumerate(contacts, start=1):
        if not isinstance(contact, dict):
            raise RuntimeError(f'Emergency dataset entry {index} must be an object.')
        if not contact.get('service') or not contact.get('number'):
            raise RuntimeError(f'Emergency dataset entry {index} is missing service or number.')


def validate_datasets():
    complaint_files, valid_rows = validate_complaint_datasets()
    validate_priority_rules()
    validate_emergency_dataset()
    print(f'Validated {len(complaint_files)} complaint file(s) and {len(valid_rows)} complaint rows.')
    print('Priority rules and emergency contacts look valid.')


if __name__ == '__main__':
    try:
        validate_datasets()
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f'VALIDATION FAILED: {exc}')
        sys.exit(1)
