// Keep the citizen report form and official case filter on the same category set.
export const CIVIC_CATEGORIES = Object.freeze([
  'Road Damage',
  'Garbage',
  'Street Light',
  'Water Leakage',
  'Drainage',
  'Electricity',
  'Tree Fallen',
  'Illegal Dumping',
  'Flood',
  'Fire',
  'Traffic Signal',
  'Public Property Damage',
  'Animal Issue',
  'Medical Emergency',
]);

const CATEGORY_TEXT_HINTS = {
  'Road Damage': ['pothole', 'road damage', 'road crack', 'damaged road'],
  Garbage: ['garbage', 'trash', 'rubbish', 'waste overflow'],
  'Street Light': ['street light', 'streetlight', 'lamp post'],
  'Water Leakage': ['water leak', 'pipe leak', 'burst pipe', 'leaking pipe'],
  Drainage: ['blocked drain', 'drainage', 'clogged drain', 'sewer blockage'],
  Electricity: ['electric wire', 'power line', 'transformer', 'power outage'],
  'Tree Fallen': ['fallen tree', 'tree fell', 'uprooted tree', 'fallen branch'],
  'Illegal Dumping': ['illegal dumping', 'dumped waste', 'dumping waste'],
  Flood: ['flood', 'flooded', 'waterlogging', 'waterlogged'],
  Fire: ['fire', 'flames', 'burning', 'blaze', 'smoke'],
  'Traffic Signal': ['traffic signal', 'signal light', 'traffic light'],
  'Public Property Damage': ['vandalism', 'damaged public property', 'broken public bench'],
  'Animal Issue': ['stray animal', 'injured animal', 'animal issue'],
  'Medical Emergency': ['medical emergency', 'injured person', 'unconscious', 'needs ambulance'],
};

// A simple wording cue only; it must never be presented as image detection.
export function findCategoryMention(text, selectedCategory) {
  const normalized = String(text || '').toLowerCase();
  if (!normalized.trim()) return null;
  const candidates = Object.entries(CATEGORY_TEXT_HINTS)
    .filter(([category, terms]) => category !== selectedCategory && terms.some(term => normalized.includes(term)))
    .sort((left, right) => Math.max(...right[1].map(term => term.length)) - Math.max(...left[1].map(term => term.length)));
  return candidates[0]?.[0] || null;
}
