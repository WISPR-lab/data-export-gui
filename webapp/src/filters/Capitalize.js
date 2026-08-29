/*
Copyright 2020 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// NOTICE --- MODIFIED FOR anonymous-research-group/data-export-gui
// extra irregular capitalization rules + title case

export const IRREGULAR_CAPS = {
  webview: 'WebView',
  whatsapp: 'WhatsApp',
  youtube: 'YouTube',
  ios: 'iOS',
  macos: 'macOS',
  os: 'OS',
  id: 'ID',
  ip: 'IP',
  ips: 'IPs',
  url: 'URL',
  ua: 'UA',
  iphone: 'iPhone',
  ipad: 'iPad',
  imac: 'iMac',
  xr: 'XR',
  xs: 'XS',
  se: 'SE',
  ipod: 'iPod',
  macbook: 'MacBook',
  tv: 'TV',
  sim: 'SIM',
  pc: 'PC',
  apple: 'Apple',
  android: 'Android',
  samsung: 'Samsung',
  safari: 'Safari',
  chrome: 'Chrome',
  firefox: 'Firefox',
  oneplus: 'OnePlus',
  pixel: 'Pixel',
};

export function capitalize(input) {
  if (!input) return '';
  return String(input)
    .split(/\s+/)
    .map(word => {
      const lower = word.toLowerCase();
      return IRREGULAR_CAPS[lower] !== undefined ? IRREGULAR_CAPS[lower] : (word.charAt(0).toUpperCase() + word.slice(1));
    })
    .join(' ');
}

export default {
  name: 'capitalize',
  filter: capitalize
}
