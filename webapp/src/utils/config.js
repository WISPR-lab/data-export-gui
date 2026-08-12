// Shared config loader - parses config.yaml once and caches result
import yaml from 'js-yaml';
import { getLogger } from '@/utils/logger';

const logger = getLogger('Config');
let config = null;

export async function loadConfig() {
  if (config) return config;
  
  const response = await fetch('./config.yaml');
  if (!response.ok) {
    throw new Error('Failed to load config.yaml: ' + response.statusText);
  }
  
  const text = await response.text();
  config = yaml.load(text);
  logger.debug('Loaded:', config);
  
  return config;
}

export function getConfig() {
  if (!config) {
    throw new Error('Config not loaded yet. Call loadConfig() first.');
  }
  return config;
}
