const childProcess = require('node:child_process');
const path = require('node:path');
const script = path.join(__dirname, 'package_vsix.py');
const candidates = process.platform === 'win32' ? ['py', 'python'] : ['python3', 'python'];
let lastError;
for (const executable of candidates) {
  const result = childProcess.spawnSync(executable, [script], { stdio: 'inherit' });
  if (!result.error && result.status === 0) process.exit(0);
  lastError = result.error ?? new Error(`${executable} exited with ${result.status}`);
}
throw lastError;
