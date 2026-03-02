export const PLATFORM_METADATA = {
  google:    { name: 'Google',    icon: 'mdi-google'    },
  discord:   { name: 'Discord',   icon: 'mdi-discord'   },
  apple:     { name: 'Apple',     icon: 'mdi-apple'     },
  facebook:  { name: 'Facebook',  icon: 'mdi-facebook'  },
  instagram: { name: 'Instagram', icon: 'mdi-instagram' },
  snapchat:  { name: 'Snapchat',  icon: 'mdi-snapchat'  },
};


export function getPlatformName(platformId) {
  const platform = PLATFORM_METADATA[platformId];
  return platform ? platform.name : 'Unknown Platform';
}


export function getPlatformIcon(platformId) {
  const platform = PLATFORM_METADATA[platformId];
  return platform ? platform.icon : 'mdi-package';
}


export function validateFile(file) {
  const errors = [];

  if (!file) {
    return { valid: false, errors: ['No file selected'] };
  }

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


export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}


export function stripZipExtension(filename) {
  return filename.replace(/\.zip$/i, '');
}
