const fs = require('node:fs');
for (const name of ['dist', 'c2000-debug-0.1.0.vsix']) {
  fs.rmSync(name, { recursive: true, force: true });
}
