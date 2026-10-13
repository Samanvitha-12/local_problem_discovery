# Indian state, district, and sub-district directory

`india_subdistricts_lgd.csv` is a public export of the Government of India's
Local Government Directory (LGD), maintained by the Ministry of Panchayati
Raj. LGD is the source for state, district, and sub-district relationships.

- Official LGD catalog: https://www.data.gov.in/catalog/local-government-directory-lgd
- LGD portal: https://lgdirectory.gov.in/downloadDirectory.do
- Export mirror used for this snapshot: https://gist.github.com/planemad/b2195c7feb506f8436659f36da1e58af
- Retrieved: 2026-10-05

`services/location_directory.py` normalizes the two Karnataka district updates
that are absent from this export snapshot (Bengaluru South and Vijayanagara),
and combines the Daman and Diu and Dadra and Nagar Haveli Union Territories.
Refresh the CSV from LGD and review current NIC district portals when updating
this file.
