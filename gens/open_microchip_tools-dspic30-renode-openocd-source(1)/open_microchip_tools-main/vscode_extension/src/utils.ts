export function stringify(result: unknown): string {
  return JSON.stringify(result, null, 2);
}