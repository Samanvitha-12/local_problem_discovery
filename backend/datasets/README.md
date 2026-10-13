Dataset ingestion and local civic dataset layout

This folder organizes datasets used for AI training.

Local civic image datasets are now available directly under backend/datasets/ with one folder per category:
- road_damage
- garbage
- street_light
- water_leakage
- drainage
- electricity
- tree_fallen
- flood
- illegal_dumping
- traffic_signal

Each category folder contains local PNG image files that can be used directly for training and testing.

The complaint-text dataset is available at backend/datasets/processed/text/complaints/.

The provided downloader supports two source types for additional datasets:
 - kaggle_slug: dataset slug usable with the Kaggle CLI (requires KAGGLE_USERNAME & KAGGLE_KEY)
 - url: direct URL to a repository, archive, or dataset page

Steps to download additional datasets

1. Install requirements in the backend virtual environment:

   pip install -r requirements.txt

2. For Kaggle downloads only: provide Kaggle API credentials as environment variables (recommended):

   For PowerShell:
     $env:KAGGLE_USERNAME = 'your-kaggle-username'
     $env:KAGGLE_KEY = 'your-kaggle-key'

   Or set them in your OS environment before starting the script.

   NOTE: Do NOT commit your Kaggle credentials into source control.

3. Edit backend/datasets/dataset_list.yml to include the datasets you want. Each entry may include either "kaggle_slug" or "url".

4. Run the downloader from the backend folder:

   cd backend
   python .\scripts\download_kaggle_datasets.py

5. Results

 - Additional datasets will be downloaded under backend/datasets/raw/<identifier>/ and backend/datasets/download_manifest.yaml will list which downloads succeeded.
 - If an entry uses a GitHub URL and git is available, the script will attempt a 'git clone'.
 - If an entry points to a ZIP or an archive URL, the script will download and unzip it.

Troubleshooting

- If URL downloads fail because 'requests' is missing, install requirements with pip.
- If a GitHub clone fails due to missing git, install git or provide the ZIP archive URL instead.
