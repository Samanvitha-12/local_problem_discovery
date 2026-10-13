# Emergency contact data

`india_emergency_numbers.json` is a verified lookup table, not an ML training
dataset. The application maps each complaint category to one or more entries in
its `categories` arrays, then only shows actions listed in `channels`.

- `112` supports voice calls and SMS through India's Emergency Response Support
  System. The UI opens the user's phone/SMS app with a prefilled message; the
  user chooses whether to send it.
- `1070`, `1073`, and `102` are listed as call-only category-specific contacts.
- Entries with a local or non-numeric contact value are informational and do not
  get a Call or SMS action.

Sources are stored beside each number in the JSON. Recheck those official sources
before changing a number or enabling another communication channel.
