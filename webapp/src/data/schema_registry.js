import yaml from 'js-yaml';

const PLATFORMS = ['facebook', 'apple', 'instagram', 'discord'];

export class ConfigLoader {
  constructor() {
    this.whitelistPatterns = [];
    this.pathMappings = new Map(); // Store adapter hints if needed
  }

  async loadSchemas() {
    console.log('[ConfigLoader] Loading schemas...');
    for (const platform of PLATFORMS) {
      try {
        const response = await fetch(`/schemas/${platform}.yaml`);
        if (!response.ok) {
          console.warn(`[ConfigLoader] Skipped ${platform}: ${response.statusText}`);
          continue;
        }
        const text = await response.text();
        const doc = yaml.load(text);
        this._processSchema(doc);
      } catch (e) {
        console.error(`[ConfigLoader] Failed to load schema for ${platform}`, e);
      }
    }
    console.log(`[ConfigLoader] Loaded ${this.whitelistPatterns.length} path patterns.`);
  }

  _processSchema(doc) {
    if (!doc.data_types) return;
    
    for (const type of doc.data_types) {
      if (!type.files) continue;
      for (const file of type.files) {
         if (file.path) {
           // Create regex from path. 
           // Escape special regex chars
           const escaped = file.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
           // Match end of string (suffix) because Takeouts often have variable prefixes
           // e.g. "Takeout/Facebook/activity.json" vs "activity.json"
           // We use a boundary check or just endsWith logic via regex
           const pattern = new RegExp(`${escaped}$`, 'i');
           this.whitelistPatterns.push(pattern);
           
           // Store mapping for ingest context later if needed
           // this.pathMappings.set(file.path, type.category); 
         }
      }
    }
  }

  /**
   * Checks if a filename matches any of the interesting file patterns
   * @param {string} filename 
   * @returns {boolean}
   */
  isWhitelisted(filename) {
    return this.whitelistPatterns.some(pattern => pattern.test(filename));
  }
}
