// added for anonymous-research-group/data-export-gui
import { capitalize } from '@/filters/Capitalize.js';

export function getCondensedOS(osName, versions) {
  const name = osName || '';
  const list = (versions || []).filter(Boolean);
  if (!name) return [];
  const titleName = capitalize(name);
  if (list.length > 0) {
    const listCopy = [...list];
    listCopy.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
    return listCopy.map(function(v, idx) {
      return idx === 0 ? (titleName + ' ' + v) : v;
    });
  }
  return [titleName];
}

export default {
  name: 'getCondensedOS',
  filter: getCondensedOS
};
