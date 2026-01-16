/**
 * uploadFormUtils.js
 * 
 * Utilities for upload form: platform metadata, file validation, formatting.
 * Keeps component clean and logic reusable.
 */

export const PLATFORM_METADATA = {
  google: { name: 'Google Takeout', icon: 'mdi-google' },
  discord: { name: 'Discord', icon: 'mdi-discord' },
  apple: { name: 'Apple Data', icon: 'mdi-apple' },
  facebook: { name: 'Facebook/Meta', icon: 'mdi-facebook' },
  instagram: { name: 'Instagram', icon: 'mdi-instagram' },
  snapchat: { name: 'Snapchat', icon: 'mdi-snapchat' },
};

/**
 * Get platform display name
 */
export function getPlatformName(platformId) {
  const platform = PLATFORM_METADATA[platformId];
  return platform ? platform.name : 'Unknown Platform';
}

/**
 * Get platform icon
 */
export function getPlatformIcon(platformId) {
  const platform = PLATFORM_METADATA[platformId];
  return platform ? platform.icon : 'mdi-package';
}

/**
 * Validate uploaded file
 * 
 * @param {File} file - File object from input
 * @returns {Object} { valid: boolean, errors: string[] }
 */
export function validateFile(file) {
  const errors = [];

  if (!file) {
    return { valid: false, errors: ['No file selected'] };
  }

  // Check file type
  if (!file.name.toLowerCase().endsWith('.zip')) {
    errors.push('Please select a ZIP file');
  }

  // Check file size (max 5GB)
  const maxSize = 5 * 1024 * 1024 * 1024;
  if (file.size > maxSize) {
    errors.push('File size exceeds 5GB limit');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Format file size for display
 * 
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size (e.g., "1.5 MB")
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Extract filename without extension
 * 
 * @param {string} filename - Full filename
 * @returns {string} Filename without extension
 */
export function stripZipExtension(filename) {
  return filename.replace(/\.zip$/i, '');
}
