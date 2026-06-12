/**
 * EXAMPLES
 * 
 *  Native Mobile App (Direct App)
 *    - Input:   { client_name: "Instagram", secondary_client: "", os_type: "ios" }
 *    - Output:  "Instagram App"
 *    
 *    - Input: {client_name: "Google Maps",  os_type: "ios"}
 *    - Output: "Google Maps App" (even without "app" in client name)
 * 
 * Mobile App Wrapped in WebView (Container App)
 *    - Input:   { client_name: "Mobile Safari :: Gmail", os_type: "ios" }
 *    - Output:  "Gmail App (Safari WebView)"
 * 
 * Web Service on Desktop Browser (Direct Web)
 *    - Input:   { client_name: "Chrome :: Gmail", os_type: "macos" }
 *    - Output:  "Gmail (Chrome)"
 * 
 * Standard Mobile Web Browsing (Direct Mobile Web)
 *    - Input:   { client_name: "Mobile Safari", os_type: "ios", platform: "google" }
 *    - Output:  "Google (Safari)"
 * 
 */


import { titleCase } from '@/filters/TitleCase.js';

function isBrowserName(name) {
  if (!name) return false;
  const n = name.toLowerCase();
  return ['chrome', 'safari', 'firefox', 'opera', 'edge', 'ie', 'browser', 'webview'].some(b => n.includes(b));
}

function getCleanBrowserName(primary) {
  const clean = titleCase(primary);
  return clean.includes('WebView') ? 'WebView' : clean.replace(/Mobile\s*/gi, '').trim();
}

// Helper to ensure a service name does not end up with double "App" suffixing
function formatAppService(serviceName) {
  if (!serviceName || !serviceName.trim()) return '';
  const lower = serviceName.toLowerCase();
  const hasAppSuffix = lower.endsWith('app') || lower.includes('for ios') || lower.includes('for android') || lower.includes('for mobile');
  return hasAppSuffix ? serviceName : `${serviceName} App`;
}

export function getUASummary(deviceInstances) {
  if (!deviceInstances || deviceInstances.length === 0) {
    return [];
  }

  const uniqueSummaryItems = {};

  deviceInstances.forEach(instance => {
    const rawName = instance.client_name || '';
    let primary = rawName;
    let secondary = '';
    
    if (rawName.includes(' :: ')) {
      const parts = rawName.split(' :: ');
      primary = parts[0].trim();
      secondary = parts[1].trim();
    }

    const platform = (instance.platform || '').trim();
    const osType = (instance.os_type || '').toLowerCase();
    const isMobile = ['ios', 'android'].includes(osType);

    const cleanPrimary = titleCase(primary);
    const cleanSecondary = titleCase(secondary);
    const primaryIsBrowser = isBrowserName(cleanPrimary);
    
    const cleanBrowser = getCleanBrowserName(cleanPrimary);
    // WebView label representation (e.g. "Safari WebView" or "WebView")
    const webViewRepr = cleanBrowser.toLowerCase() === 'webview' ? 'WebView' : `${cleanBrowser} WebView`;

    let label1 = '';
    let label2 = '';

    if (isMobile) {
      if (!primaryIsBrowser) {
        // 1 -- native mobile app
        // "gmail" + ios --> "Gmail App"
        // "google maps" + android --> "Google Maps App"
        const service = platform === 'google' ? (cleanSecondary || cleanPrimary) : titleCase(platform);
        label1 = formatAppService(service);
        label2 = '';
      } else if (primaryIsBrowser && secondary) {
        // 2 -- mobile in-app webview
        // "mobile safari :: gmail" + ios --> "Gmail App" (Safari WebView)
        // TODO example with facebook? look at existing UAs
        // i guess we don't know how this works with browsing in chrome. other signature?
        const service = platform === 'google' ? cleanSecondary : titleCase(platform);
        label1 = formatAppService(service);
        label2 = webViewRepr;

      } else {
        // 3 -- mobile web browsing
        // "mobile safari" + ios + google --> "Google (Safari)"
        //label1 = platform === 'google' ? 'Google' : titleCase(platform);
        //label2 = cleanBrowser;
        // update:  "mobile safari" + ios + google --> "Safari"
        label1 = cleanBrowser;
      }
    } else {
      if (!primaryIsBrowser) {
        // 4 -- desktop app (if client name is not a browser, assume it's a desktop app)
        // "slack" + macos --> "Slack App"
        label1 = cleanPrimary;
        label2 = '';
      } else if (primaryIsBrowser && secondary) {
        // 5 -- desktop in-app webview
        // "chrome :: gmail" + macos --> "Gmail (Chrome)"
        // "chrome :: slack" + macos --> "Slack (Chrome)"
        label1 = platform === 'google' ? cleanSecondary : titleCase(platform);
        label2 = cleanBrowser;
      } else {
        // 6 -- desktop web browsing
        // "chrome" + macos + google --> "Google (Chrome)"
        // label1 = platform === 'google' ? 'Google' : titleCase(platform);
        // label2 = cleanBrowser;
        // update:  "chrome" + macos + google --> "Chrome"
        label1 = cleanBrowser
      }
    }

    const isUnknown = !platform || platform.toLowerCase() === 'unknown';

    const color = instance.upload_color;
    const displayPlatform = titleCase(platform);
    const key = `${displayPlatform}-${color}`;
    if (!uniqueSummaryItems[key]) {
      uniqueSummaryItems[key] = {
        primary: label1,
        secondary: label2,
        color,
        isUnknown: !!isUnknown,
        platform: displayPlatform
      };
    }
  });

  return Object.values(uniqueSummaryItems);
}
