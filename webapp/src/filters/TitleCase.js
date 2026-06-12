// added for WISPR-lab/data-export-gui

export const IRREGULAR_CAPS = {
  webview: 'WebView',
  whatsapp: 'WhatsApp',
  youtube: 'YouTube',
  ios: 'iOS',
  macos: 'macOS',
  os: 'OS',
};

export function titleCase(str) {
  if (!str) return '';
  return str
    .split(/\s+/)
    .map(word => {
      const lower = word.toLowerCase();
      return IRREGULAR_CAPS[lower] !== undefined ? IRREGULAR_CAPS[lower] : (word.charAt(0).toUpperCase() + word.slice(1));
    })
    .join(' ');
}

export default {
  name: 'titleCase',
  filter: titleCase
}
