// added for WISPR-lab/data-export-gui
export default {
  name: 'formatDeviceDetails',
  filter: function (input) {
    if (!input) return '';
    let str = input.toString();

    const replacements = {
      'iphone': 'iPhone',
      'ios': 'iOS',
      'apple': 'Apple',
      'ipad': 'iPad',
      'ipod': 'iPod',
      'macbook': 'MacBook',
      'macos': 'macOS',
      'android': 'Android',
      'samsung': 'Samsung',
      'safari': 'Safari',
      'chrome': 'Chrome',
      'firefox': 'Firefox',
      'xr': 'XR',
      'xs': 'XS',
      'se': 'SE',
      'oneplus': 'OnePlus',
      'pixel': 'Pixel'
    };

    // replace specific words case-insensitively
    Object.entries(replacements).forEach(([lower, correct]) => {
      const regex = new RegExp(`\\b${lower}\\b`, 'gi');
      str = str.replace(regex, correct);
    });

    // fallback: title case other fully lowercase words (e.g. "galaxy s20" -> "Galaxy S20")
    str = str.replace(/\b([a-z])([a-z]*)\b/g, (match, p1, p2) => {
      const lowerWord = match.toLowerCase();
      if (replacements[lowerWord]) {
        return replacements[lowerWord];
      }
      if (lowerWord.startsWith('sm-')) {
        return match;
      }
      return p1.toUpperCase() + p2;
    });

    return str;
  }
}
