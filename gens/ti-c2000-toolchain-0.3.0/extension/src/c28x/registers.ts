import { Architecture } from '../protocol';

export interface RegisterDefinition {
  name: string;
  bits: number;
  group: string;
}

const C28X_BASE: RegisterDefinition[] = [
  { name: 'ACC', bits: 32, group: 'Core' },
  { name: 'P', bits: 32, group: 'Core' },
  { name: 'XT', bits: 32, group: 'Core' },
  ...Array.from({ length: 8 }, (_, index) => ({ name: `XAR${index}`, bits: 32, group: 'Address' })),
  { name: 'SP', bits: 16, group: 'Address' },
  { name: 'DP', bits: 16, group: 'Address' },
  { name: 'IFR', bits: 16, group: 'Status' },
  { name: 'IER', bits: 16, group: 'Status' },
  { name: 'DBGIER', bits: 16, group: 'Status' },
  { name: 'ST0', bits: 16, group: 'Status' },
  { name: 'ST1', bits: 16, group: 'Status' },
  { name: 'PC', bits: 32, group: 'Control' },
  { name: 'RPC', bits: 32, group: 'Control' },
  { name: 'RB', bits: 32, group: 'Control' },
  { name: 'RAS', bits: 32, group: 'Control' },
];

const FPU: RegisterDefinition[] = [
  ...Array.from({ length: 8 }, (_, index) => ({ name: `R${index}H`, bits: 32, group: 'FPU' })),
  { name: 'STF', bits: 32, group: 'FPU' },
];

const VCU: RegisterDefinition[] = [
  { name: 'VCRC', bits: 32, group: 'VCU' },
  { name: 'VSTATUS', bits: 32, group: 'VCU' },
];

const TMU: RegisterDefinition[] = [
  { name: 'TMU_STATUS', bits: 32, group: 'TMU' },
];

const CORTEX_M3: RegisterDefinition[] = [
  ...Array.from({ length: 13 }, (_, index) => ({ name: `R${index}`, bits: 32, group: 'Core' })),
  { name: 'SP', bits: 32, group: 'Core' },
  { name: 'LR', bits: 32, group: 'Core' },
  { name: 'PC', bits: 32, group: 'Core' },
  { name: 'XPSR', bits: 32, group: 'Status' },
  { name: 'MSP', bits: 32, group: 'Special' },
  { name: 'PSP', bits: 32, group: 'Special' },
  { name: 'PRIMASK', bits: 32, group: 'Special' },
  { name: 'BASEPRI', bits: 32, group: 'Special' },
  { name: 'FAULTMASK', bits: 32, group: 'Special' },
  { name: 'CONTROL', bits: 32, group: 'Special' },
];

export function profileFor(device: string, architecture: Architecture, override = 'auto'): RegisterDefinition[] {
  if (override === 'cortex-m3' || architecture === 'cortex-m3') {
    return CORTEX_M3;
  }
  if (override === 'c28x') {
    return C28X_BASE;
  }
  if (override === 'c28x-fpu-vcu') {
    return [...C28X_BASE, ...FPU, ...VCU];
  }
  if (override === 'c28x-fpu-tmu-vcu') {
    return [...C28X_BASE, ...FPU, ...TMU, ...VCU];
  }

  const normalized = device.toLowerCase();
  if (normalized.includes('280049')) {
    return [...C28X_BASE, ...FPU, ...TMU, ...VCU];
  }
  if (normalized.includes('28069')) {
    return [...C28X_BASE, ...FPU, ...VCU];
  }
  if (normalized.includes('28m35')) {
    return [...C28X_BASE, ...FPU];
  }
  return C28X_BASE;
}
