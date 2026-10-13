"""Location data sourced from the Government of India's Local Government Directory."""
import csv
import re
from functools import lru_cache
from pathlib import Path


LGD_CSV = Path(__file__).resolve().parents[1] / 'datasets' / 'india_subdistricts_lgd.csv'


def _normalise(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


@lru_cache(maxsize=1)
def _directory():
    """Load LGD state → district → sub-district (taluk) relationships once."""
    locations = {}
    with LGD_CSV.open('r', encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            state = (row.get('State Name (In English)') or '').strip().title()
            district = (row.get('District Name (In English)') or '').strip().title()
            taluk = (row.get('Sub-District Name') or '').strip().title()
            if not state or not district or not taluk:
                continue
            locations.setdefault(state, {}).setdefault(district, set()).add(taluk)

    # Daman and Diu and Dadra and Nagar Haveli are now one Union Territory.
    dadra = locations.pop('Dadra And Nagar Haveli', {})
    daman = locations.pop('Daman And Diu', {})
    merged_ut = locations.setdefault('Dadra And Nagar Haveli And Daman And Diu', {})
    for district_map in (dadra, daman):
        for district, taluks in district_map.items():
            merged_ut.setdefault(district, set()).update(taluks)

    # The current Karnataka government district directory uses these names;
    # the LGD export still carries the earlier district boundaries/names.
    karnataka = locations.setdefault('Karnataka', {})
    old_ramanagara = karnataka.pop('Ramanagara', set())
    karnataka['Bengaluru South'] = old_ramanagara | {
        'Ramanagara', 'Channapatna', 'Kanakapura', 'Magadi', 'Harohalli'
    }
    karnataka['Vijayanagara'] = {
        'Kudligi', 'H.B.Halli', 'Hadagali', 'Hospet', 'Harapanahalli', 'Kottur'
    }
    ballari = karnataka.get('Ballari', set())
    ballari.difference_update({'Hagaribommanahalli', 'Hadagali', 'Harapanahalli', 'Hosapete', 'Kudligi'})
    locations['Karnataka']['Ballari'] = ballari
    return locations


def get_location_directory():
    return [
        {
            'name': state,
            'districts': [
                {'name': district, 'taluks': sorted(taluks, key=str.casefold)}
                for district, taluks in sorted(districts.items(), key=lambda item: item[0].casefold())
            ],
        }
        for state, districts in sorted(_directory().items(), key=lambda item: item[0].casefold())
    ]


def is_valid_location(state, district, taluk):
    locations = _directory()
    state_name = next((name for name in locations if _normalise(name) == _normalise(state)), None)
    if state_name is None:
        return False
    district_name = next(
        (name for name in locations[state_name] if _normalise(name) == _normalise(district)),
        None,
    )
    if district_name is None:
        return False
    return any(_normalise(name) == _normalise(taluk) for name in locations[state_name][district_name])
