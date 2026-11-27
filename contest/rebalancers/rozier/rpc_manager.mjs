export function initializeProvider() {}
export function getProvider() { return null; }
export function getWallet() { return null; }
export function rotateToNextRPC() {}
export function shouldRotateRPC() { return false; }
export async function executeWithFallback(fn) { return fn(); }
export function getCurrentRPC() { return 'stand-in'; }
export function getCurrentRPCName() { return 'stand-in'; }
export function getRPCStats() { return {}; }
export function resetRPCStats() {}
export async function testAllRPCs() { return []; }
