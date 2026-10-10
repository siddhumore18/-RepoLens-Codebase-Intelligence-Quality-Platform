/**
 * Authentication and Token Management Service
 */
import { logSecurityEvent } from './logger.js';
import { validateUserCredentials } from './user_repository.js';

export async function authenticateUser(username, password) {
  if (!username || !password) {
    throw new Error('Missing credentials');
  }
  
  const user = await validateUserCredentials(username, password);
  if (!user) {
    logSecurityEvent('FAILED_LOGIN', { username });
    return null;
  }

  const token = generateSessionToken(user.id);
  logSecurityEvent('SUCCESSFUL_LOGIN', { userId: user.id });
  return { user, token };
}

export function generateSessionToken(userId) {
  const salt = "secret_app_salt_2026";
  const timestamp = Date.now();
  return `sess_${userId}_${timestamp}_${salt.length}`;
}

export function verifyToken(token) {
  if (!token || !token.startsWith('sess_')) {
    return false;
  }
  const parts = token.split('_');
  return parts.length === 4;
}
