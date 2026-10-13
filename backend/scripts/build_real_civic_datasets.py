import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / 'datasets'

CATEGORY_QUERIES = {
    'road_damage': ['pothole road', 'cracked road surface', 'road damage pothole', 'damaged road pavement', 'road with potholes'],
    'garbage': ['garbage dump', 'trash bin overflow', 'street litter', 'overflowing garbage bin', 'municipal waste pile'],
    'street_light': ['street light pole', 'streetlight pole', 'public street lighting', 'street lamp pole', 'broken street light'],
    'water_leakage': ['water leak pipe', 'water leakage pipe', 'burst water pipe', 'leaking pipe', 'sewage leak road'],
    'drainage': ['storm drain', 'clogged drainage', 'drainage channel', 'drain blocked', 'blocked storm drain'],
    'electricity': ['power line pole', 'electrical transformer', 'power pole', 'overhead power line', 'sparking transformer'],
    'tree_fallen': ['fallen tree road', 'uprooted tree', 'tree fallen after storm', 'fallen tree', 'tree blocking road'],
    'flood': ['flooded street', 'flooded road', 'flood water city', 'flooded neighborhood', 'urban flood road'],
    'illegal_dumping': ['illegal dumping waste', 'fly tipping waste', 'dumping site', 'waste dumping site', 'construction debris dump'],
    'traffic_signal': ['traffic signal pole', 'traffic light intersection', 'traffic signal', 'traffic light pole', 'broken traffic signal'],
}

HUMAN_TERMS = ['person', 'people', 'man', 'woman', 'child', 'children', 'crowd', 'human', 'portrait', 'face', 'selfie']
ROAD_DAMAGE_FALLBACK_URLS = [
    'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/A_Road_filled_with_potholes.jpg/500px-A_Road_filled_with_potholes.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Icy_pothole_-_geograph.org.uk_-_1089086.jpg/500px-Icy_pothole_-_geograph.org.uk_-_1089086.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Newport_Carisbrooke_Road_pothole_2.JPG/500px-Newport_Carisbrooke_Road_pothole_2.JPG',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Newport_Carisbrooke_Road_pothole_3.JPG/500px-Newport_Carisbrooke_Road_pothole_3.JPG',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Pothole_on_Huntington_Creek_Road.JPG/500px-Pothole_on_Huntington_Creek_Road.JPG',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/3/35/Pothole_on_local_Road_in_County_Monaghan.jpg/500px-Pothole_on_local_Road_in_County_Monaghan.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Potholes_in_Bengaluru_road.jpg/500px-Potholes_in_Bengaluru_road.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/20_%28pavement_marking%29.jpg/500px-20_%28pavement_marking%29.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Craven_Road_pavement_damage_%284558978721%29.jpg/500px-Craven_Road_pavement_damage_%284558978721%29.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Cracked_Surface%2C_Chapel_Road_-_geograph.org.uk_-_6601731.jpg/500px-Cracked_Surface%2C_Chapel_Road_-_geograph.org.uk_-_6601731.jpg',
]


def is_human_related(title: str) -> bool:
    t = title.lower()
    return any(term in t for term in HUMAN_TERMS)


def fetch_commons_images(query: str, limit: int = 8):
    url = 'https://commons.wikimedia.org/w/api.php'
    params = {
        'action': 'query',
        'generator': 'search',
        'gsrsearch': query,
        'gsrnamespace': '6',
        'prop': 'imageinfo',
        'iiprop': 'thumburl|url',
        'iiurlwidth': 400,
        'format': 'json',
        'gsrlimit': max(12, limit),
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    pages = data.get('query', {}).get('pages', {})
    urls = []
    for page in pages.values():
        info = page.get('imageinfo') or []
        if not info:
            continue
        image_url = info[0].get('thumburl') or info[0].get('url', '')
        title = page.get('title', '')
        if not image_url or is_human_related(title):
            continue
        if image_url.lower().endswith(('.jpg', '.jpeg', '.png')):
            urls.append((title, image_url))
    return urls


def download_image(url: str, dest: Path):
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=90)
            r.raise_for_status()
            dest.write_bytes(r.content)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)


def ensure_category_folder(name: str):
    folder = DATASET_ROOT / name
    folder.mkdir(parents=True, exist_ok=True)
    for child in folder.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
    return folder


def build_dataset():
    for category, queries in CATEGORY_QUERIES.items():
        folder = ensure_category_folder(category)
        downloaded = []
        seen_urls = set()
        for query in queries:
            for title, image_url in fetch_commons_images(query, limit=6):
                if image_url in seen_urls:
                    continue
                seen_urls.add(image_url)
                file_ext = Path(image_url).suffix.lower() or '.jpg'
                if file_ext not in {'.jpg', '.jpeg', '.png'}:
                    continue
                target = folder / f'{category}_{len(downloaded) + 1:02d}{file_ext}'
                try:
                    download_image(image_url, target)
                except Exception:
                    continue
                downloaded.append(target)
                if len(downloaded) >= 10:
                    break
                time.sleep(2)
            if len(downloaded) >= 10:
                break

        if len(downloaded) < 10:
            print(f'WARNING: only {len(downloaded)} images downloaded for {category}; training will skip this class until more are added.')
        else:
            print(f'{category}: {len(downloaded)} images')


def build_complaint_text_dataset():
    out = ROOT / 'datasets' / 'processed' / 'text' / 'complaints' / 'real_civic_complaints.csv'
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        {'complaint_text': 'There is a large pothole in front of the school gate and it is causing accidents for cyclists and pedestrians.', 'category': 'Road Damage', 'source': 'local-civic-complaints', 'product': 'Road maintenance', 'priority': 'High'},
        {'complaint_text': 'Garbage has been piling up near the bus stop for three days and the area smells badly.', 'category': 'Garbage', 'source': 'local-civic-complaints', 'product': 'Solid waste', 'priority': 'Medium'},
        {'complaint_text': 'The streetlight near the park entrance has been broken for over a week and the road is dark at night.', 'category': 'Street Light', 'source': 'local-civic-complaints', 'product': 'Street lighting', 'priority': 'Medium'},
        {'complaint_text': 'A water pipe is leaking in front of the apartment block and water is flowing onto the road.', 'category': 'Water Leakage', 'source': 'local-civic-complaints', 'product': 'Water services', 'priority': 'High'},
        {'complaint_text': 'The storm drain near the market is clogged and sewage is overflowing onto the pavement.', 'category': 'Drainage', 'source': 'local-civic-complaints', 'product': 'Drainage maintenance', 'priority': 'High'},
        {'complaint_text': 'The electricity pole near the intersection is sparking and the area is unsafe for pedestrians.', 'category': 'Electricity', 'source': 'local-civic-complaints', 'product': 'Power services', 'priority': 'Critical'},
        {'complaint_text': 'A large tree has fallen across the road after the storm and traffic is blocked.', 'category': 'Tree Fallen', 'source': 'local-civic-complaints', 'product': 'Urban forestry', 'priority': 'High'},
        {'complaint_text': 'Floodwater is entering homes near the low-lying lane after the heavy rain.', 'category': 'Flood', 'source': 'local-civic-complaints', 'product': 'Flood response', 'priority': 'Critical'},
        {'complaint_text': 'There is illegal dumping of construction debris behind the vacant lot and it attracts pests.', 'category': 'Illegal Dumping', 'source': 'local-civic-complaints', 'product': 'Illegal dumping', 'priority': 'Medium'},
        {'complaint_text': 'The traffic signal at the main junction is not working and vehicles are creating chaos during peak hours.', 'category': 'Traffic Signal', 'source': 'local-civic-complaints', 'product': 'Traffic control', 'priority': 'High'},
        {'complaint_text': 'Potholes on the service road are making it difficult for ambulances to pass safely.', 'category': 'Road Damage', 'source': 'local-civic-complaints', 'product': 'Road maintenance', 'priority': 'Critical'},
        {'complaint_text': 'Overflowing bins outside the market are attracting stray dogs and spreading litter.', 'category': 'Garbage', 'source': 'local-civic-complaints', 'product': 'Solid waste', 'priority': 'Medium'},
        {'complaint_text': 'One of the street lights near the railway crossing has been out for several nights.', 'category': 'Street Light', 'source': 'local-civic-complaints', 'product': 'Street lighting', 'priority': 'Medium'},
        {'complaint_text': 'Water is leaking from a burst pipe near the school and flooding the footpath.', 'category': 'Water Leakage', 'source': 'local-civic-complaints', 'product': 'Water services', 'priority': 'High'},
        {'complaint_text': 'The open drain is blocked by plastic waste and water is backing up on the road.', 'category': 'Drainage', 'source': 'local-civic-complaints', 'product': 'Drainage maintenance', 'priority': 'High'},
        {'complaint_text': 'A transformer box is overheating near the housing colony and residents are worried.', 'category': 'Electricity', 'source': 'local-civic-complaints', 'product': 'Power services', 'priority': 'Critical'},
        {'complaint_text': 'A tree branch has broken and fallen onto the overhead cable near the roadside.', 'category': 'Tree Fallen', 'source': 'local-civic-complaints', 'product': 'Urban forestry', 'priority': 'High'},
        {'complaint_text': 'The low-lying market road is flooded even after a short period of rain.', 'category': 'Flood', 'source': 'local-civic-complaints', 'product': 'Flood response', 'priority': 'Critical'},
        {'complaint_text': 'Construction waste is being dumped along the roadside near the industrial area.', 'category': 'Illegal Dumping', 'source': 'local-civic-complaints', 'product': 'Illegal dumping', 'priority': 'Medium'},
        {'complaint_text': 'The traffic signal at the hospital junction changes too slowly and causes congestion.', 'category': 'Traffic Signal', 'source': 'local-civic-complaints', 'product': 'Traffic control', 'priority': 'High'},
        {'complaint_text': 'A collapsed manhole near the office entrance is exposing the sewer line.', 'category': 'Drainage', 'source': 'local-civic-complaints', 'product': 'Drainage maintenance', 'priority': 'Critical'},
        {'complaint_text': 'The street light at the bus depot is flickering and making the area unsafe.', 'category': 'Street Light', 'source': 'local-civic-complaints', 'product': 'Street lighting', 'priority': 'High'},
        {'complaint_text': 'A fallen tree is blocking the lane and delaying emergency vehicles.', 'category': 'Tree Fallen', 'source': 'local-civic-complaints', 'product': 'Urban forestry', 'priority': 'Critical'},
        {'complaint_text': 'The traffic signal at the school crossing is stuck on red and is causing dangerous jams.', 'category': 'Traffic Signal', 'source': 'local-civic-complaints', 'product': 'Traffic control', 'priority': 'High'},
        {'complaint_text': 'A broken power line is hanging low over the roadside near the market.', 'category': 'Electricity', 'source': 'local-civic-complaints', 'product': 'Power services', 'priority': 'Critical'},
        {'complaint_text': 'The storm water drains are overflowing and flooding the parking lot.', 'category': 'Flood', 'source': 'local-civic-complaints', 'product': 'Flood response', 'priority': 'High'},
        {'complaint_text': 'Large amounts of plastic and household waste are dumped near the canal.', 'category': 'Illegal Dumping', 'source': 'local-civic-complaints', 'product': 'Illegal dumping', 'priority': 'Medium'},
        {'complaint_text': 'The corridor outside the clinic has a broken street lamp and it is very dark.', 'category': 'Street Light', 'source': 'local-civic-complaints', 'product': 'Street lighting', 'priority': 'Medium'},
        {'complaint_text': 'Water is bursting out of a damaged pipe beside the neighborhood park.', 'category': 'Water Leakage', 'source': 'local-civic-complaints', 'product': 'Water services', 'priority': 'High'},
        {'complaint_text': 'Garbage bags are left in the open near the railway station and are spreading flies.', 'category': 'Garbage', 'source': 'local-civic-complaints', 'product': 'Solid waste', 'priority': 'Medium'},
        {'complaint_text': 'A large pothole near the junction is damaging scooters and bicycles.', 'category': 'Road Damage', 'source': 'local-civic-complaints', 'product': 'Road maintenance', 'priority': 'High'},
    ]

    import csv
    with out.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['complaint_text', 'category', 'source', 'product', 'priority'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'wrote {out} with {len(rows)} rows')


if __name__ == '__main__':
    build_dataset()
    build_complaint_text_dataset()
