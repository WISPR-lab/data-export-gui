// Attribute/column key -> label. Mechanical capitalize() by default
// (`norm__` prefix stripped first); a few keys need explicit overrides
// because the mechanical result is actually wrong/noisy, not just ugly.
import { capitalize } from './Capitalize.js';

const OVERRIDES = {
  event_type_msg: 'Event Type',
  entity_first_seen_timestamp: 'First Seen',
  entity_last_seen_timestamp: 'Last Seen',
  primary_timestamp: 'Timestamp',
  norm__model_name: 'Device Model',
  norm__manufacturer: 'Device Manufacturer',
};

function toWords(key) {
  return String(key)
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_\-.]+/g, ' ')
    .trim();
}

export function formatAttributeLabel(key) {
  if (!key) return '';
  const normalizedKey = String(key).trim();
  const lowerKey = normalizedKey.toLowerCase();
  if (OVERRIDES[lowerKey]) return OVERRIDES[lowerKey];
  const base = lowerKey.startsWith('norm__') ? normalizedKey.slice(6) : normalizedKey;
  return capitalize(toWords(base));
}

export default {
  name: 'formatAttributeLabel',
  filter: formatAttributeLabel,
}
