const fs = require('node:fs');
for (const name of ['dist', 'c2000-debug-0.3.0.vsix']) {
  fs.rmSync(name, { recursive: true, force: true });
}
