import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { execSync } from 'child_process';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const WORKER_PATH = resolve(__dirname, '../../webapp/src/pyodide/pyodide-worker.js');
const VENV_PYTHON = resolve(__dirname, '../../venv/bin/python3');

// pip package name -> Python import name (only needed where they differ)
const IMPORT_NAME = {
  'pyyaml':  'yaml',
};

function extractPackagesFromWorker() {
  const rawSrc = readFileSync(WORKER_PATH, 'utf8');
  // Strip comments to ignore commented-out installs
  const src = rawSrc.replace(/\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '');

  const packages = new Set();

  // loadPackage(['pyyaml', 'pytz', ...]) or loadPackage('micropip')
  for (const m of src.matchAll(/loadPackage\((\[.*?\]|'[^']+'|"[^"]+")\)/g)) {
    const arg = m[1].trim();
    if (arg.startsWith('[')) {
      for (const pkg of arg.matchAll(/'([^']+)'|"([^"]+)"/g)) {
        packages.add(pkg[1] || pkg[2]);
      }
    } else {
      packages.add(arg.replace(/['"]/g, ''));
    }
  }

  // Parse builtinModules = [...] definition
  const builtinMatch = src.match(/builtinModules\s*=\s*(\[.*?\])/);
  if (builtinMatch) {
    const arrayStr = builtinMatch[1];
    for (const pkg of arrayStr.matchAll(/'([^']+)'|"([^"]+)"/g)) {
      packages.add(pkg[1] || pkg[2]);
    }
  }

  // micropip.install('hjson') etc.
  for (const m of src.matchAll(/micropip\.install\(['"]([^'"]+)['"]\)/g)) {
    const pkg = m[1];
    // Ignore emfs paths or templated paths
    if (!pkg.startsWith('emfs:') && !pkg.includes('$')) {
      packages.add(pkg);
    }
  }

  // micropip itself is a Pyodide-only meta-package; skip it
  packages.delete('micropip');

  return [...packages];
}

function canImport(pkg) {
  const importName = IMPORT_NAME[pkg] || pkg;
  try {
    execSync(`${VENV_PYTHON} -c "import ${importName}"`, { stdio: 'pipe' });
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e.stderr?.toString().trim() || e.message };
  }
}

describe('Pyodide runtime dependencies (parsed from pyodide-worker.js)', () => {
  const packages = extractPackagesFromWorker();

  it('should find at least one package in pyodide-worker.js', () => {
    expect(packages.length).toBeGreaterThan(0);
  });

  for (const pkg of packages) {
    it(`${pkg} is importable in the venv`, () => {
      const { ok, error } = canImport(pkg);
      expect(ok, `'${pkg}' failed to import — install it: venv/bin/pip install ${pkg}\n${error ?? ''}`).toBe(true);
    });
  }
});
