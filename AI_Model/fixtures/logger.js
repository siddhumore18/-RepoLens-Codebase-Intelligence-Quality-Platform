/**
 * Central Structured Logging Service
 */
export function logSecurityEvent(eventType, payload) {
  const timestamp = new Date().toISOString();
  console.log(`[AUDIT] ${timestamp} | ${eventType} | ${JSON.stringify(payload)}`);
}

export function logTransaction(txId, status, amount) {
  const timestamp = new Date().toISOString();
  console.log(`[TRANSACTION] ${timestamp} | ${txId} | ${status} | ${amount}`);
}
