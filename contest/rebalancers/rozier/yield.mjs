// stand-in for yield.js (Aave V3 on Base); yield farming is switched off in the test config
export async function depositToAave() { return null; }
export async function withdrawFromAave() { return null; }
export async function getAaveBalance() { return 0; }
export async function getAaveAccountData() { return null; }
export async function optimizeUSDCAllocation() { return { action: 'none', reason: 'no Aave in the test' }; }
