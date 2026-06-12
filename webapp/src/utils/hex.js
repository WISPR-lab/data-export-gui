// added for WISPR-lab/data-export-gui

export const DEFAULT_UPLOAD_COLOR = '#5E75C2';

// normalize hex color string to always have '#' prefix
export function hexColor(color) {
  if (!color) return DEFAULT_UPLOAD_COLOR;
  const str = String(color).trim();
  if (!str) return DEFAULT_UPLOAD_COLOR;
  return str[0] === '#' ? str : '#' + str;
}
