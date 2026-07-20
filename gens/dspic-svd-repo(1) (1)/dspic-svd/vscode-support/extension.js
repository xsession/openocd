'use strict';

const path = require('path');
const vscode = require('vscode');

const DEVICES = [
  ['dsPIC30F5011', 'dspic30f5011.svd'],
  ['dsPIC33FJ128MC802', 'dspic33fj128mc802.svd'],
  ['dsPIC33FJ128MC804', 'dspic33fj128mc804.svd'],
  ['dsPIC33EP128GM604', 'dspic33ep128gm604.svd']
];

async function activate(context) {
  const extension = vscode.extensions.getExtension('marus25.cortex-debug');
  if (!extension) {
    vscode.window.showErrorMessage(
      'Cortex-Debug is required by the Microchip dsPIC device support pack.'
    );
    return;
  }

  try {
    const api = await extension.activate();
    if (!api || typeof api.registerSVDFile !== 'function') {
      console.warn(
        'Cortex-Debug did not expose registerSVDFile; use svdFile directly in launch.json.'
      );
      return;
    }
    for (const [device, filename] of DEVICES) {
      api.registerSVDFile(
        new RegExp(`^${device}$`, 'i'),
        path.join(context.extensionPath, 'data', filename)
      );
    }
  } catch (error) {
    console.error('Unable to register dsPIC SVD files with Cortex-Debug', error);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
