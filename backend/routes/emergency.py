import json
from pathlib import Path
from flask import Blueprint, jsonify

emergency_bp = Blueprint('emergency_bp', __name__)
DATASET_PATH = Path(__file__).resolve().parents[1] / 'datasets' / 'emergency' / 'india_emergency_numbers.json'
LEGACY_DATASET_PATH = Path(__file__).resolve().parents[1] / 'datasets' / 'emergency_india.json'

@emergency_bp.route('/api/emergency/india', methods=['GET'])
def get_emergency_numbers():
    for candidate in (DATASET_PATH, LEGACY_DATASET_PATH):
        if candidate.exists():
            with candidate.open('r', encoding='utf-8') as handle:
                contacts = json.load(handle)
            return jsonify({'success': True, 'data': contacts}), 200
    return jsonify({'success': False, 'data': []}), 404
