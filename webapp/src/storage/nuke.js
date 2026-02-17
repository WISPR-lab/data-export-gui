import { closeDB } from '@/database/index.js';
import { OPFSManager } from '@/storage/opfs_manager.js';




export async function wipeAllData() {
  try {
    await closeDB();
    const opfsManager = new OPFSManager();
    await opfsManager.clearOPFSFiles();
    localStorage.clear();
    
    window.location.reload();
  } catch (error) {
    console.error('[NukeData] wipeAllData failed:', error);
    alert('[NukeData] Failed to wipe data. Please refresh the page and try again.');
  }
}