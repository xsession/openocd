export type BackendResponse = {
  ok: boolean;
  result?: unknown;
  error?: string;
};

export type ToolKind = 'pk4' | 'icd4';

export type FamilyMetadata = {
  family: string;
  behavior?: string;
  notes?: string;
  programmerClass?: string;
  debuggerClass?: string;
  namedScriptCount?: number;
  supportsProgramming?: boolean;
  supportsDebugging?: boolean;
  supportsSetPc?: boolean;
  programmerRawCommandTags?: string[];
  debuggerRawCommandTags?: string[];
  programmerRawCommandGroups?: string[];
  debuggerRawCommandGroups?: string[];
  programmerRawCommandCapabilities?: string[];
  debuggerRawCommandCapabilities?: string[];
  programmerRawCommandSignatures?: string[];
  debuggerRawCommandSignatures?: string[];
};

export type HardwareSessionStatus = {
  tool?: string;
  processor?: string;
  family?: string;
  familyMetadata?: FamilyMetadata;
  hasDebugScripts?: boolean;
  hasProgrammingScripts?: boolean;
};

export type HardwareSessionStartOptions = {
  processor?: string;
  scriptsPath?: string;
  toolScriptsPath?: string;
};

export type FamilyInventoryFilterState = {
  localSearch?: string;
  searchPrefix?: string;
  behavior?: string;
  group?: string;
  signature?: string;
  capability?: string;
  families?: FamilyMetadata[];
  scrollY?: number;
};

export type FamilyInventoryMessage = {
  command?: string;
  family?: string;
  processor?: string;
  scriptsPath?: string;
  toolScriptsPath?: string;
  field?: 'scriptsPath' | 'toolScriptsPath';
  capability?: string;
  signature?: string;
  group?: string;
  searchPrefix?: string;
  families?: FamilyMetadata[];
};

export type ZephyrStubDemoMessage = {
  command?: string;
  family?: string;
  processor?: string;
  writeAddress?: string;
  writeHex?: string;
};

export type ZephyrStubDemoDefaults = {
  family: string;
  processor: string;
  writeAddress: string;
  writeHex: string;
};