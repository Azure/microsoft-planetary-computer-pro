/**
 * MSAL Authentication
 * 
 * Microsoft Entra ID authentication using MSAL.js.
 * See: https://learn.microsoft.com/azure/planetary-computer/build-web-application
 */

import { PublicClientApplication } from '@azure/msal-browser';
import { config } from './config.js';

let msalInstance = null;
let currentAccount = null;

/**
 * Initialize MSAL - exact pattern from Step 4
 */
export async function initAuth() {
  const msalConfig = {
    auth: {
      clientId: config.clientId,
      authority: `https://login.microsoftonline.com/${config.tenantId}`,
      redirectUri: window.location.origin,
    },
    cache: {
      cacheLocation: 'sessionStorage',
      storeAuthStateInCookie: false,
    },
  };
  
  msalInstance = new PublicClientApplication(msalConfig);
  await msalInstance.initialize();
  
  // Handle redirect response (if returning from login)
  try {
    const response = await msalInstance.handleRedirectPromise();
    if (response) {
      currentAccount = response.account;
      console.log('Login redirect completed successfully');
    }
  } catch (error) {
    console.error('Redirect handling error:', error);
  }
  
  // Check for existing sessions
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length > 0) {
    currentAccount = accounts[0];
  }
  
  return msalInstance;
}

/**
 * Login with popup - exact pattern from Step 4
 */
export async function login() {
  if (!msalInstance) {
    await initAuth();
  }
  
  const loginRequest = {
    scopes: [config.scope],
  };
  
  // Use redirect instead of popup to avoid COOP issues in modern browsers
  await msalInstance.loginRedirect(loginRequest);
  // Note: This will redirect away from the page, then back after auth
  // The account will be set in initAuth when the page reloads
}

/**
 * Logout
 */
export async function logout() {
  if (msalInstance && currentAccount) {
    await msalInstance.logoutRedirect({
      account: currentAccount,
    });
    currentAccount = null;
  }
}

/**
 * Get access token - exact pattern from Step 4
 */
export async function getAccessToken() {
  if (!msalInstance) {
    throw new Error('MSAL not initialized. Call initAuth() first.');
  }
  
  if (!currentAccount) {
    throw new Error('Not logged in. Call login() first.');
  }
  
  const tokenRequest = {
    scopes: [config.scope],
    account: currentAccount,
  };
  
  try {
    const response = await msalInstance.acquireTokenSilent(tokenRequest);
    return response.accessToken;
  } catch (error) {
    // Silent token acquisition failed, try redirect
    await msalInstance.acquireTokenRedirect(tokenRequest);
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  return currentAccount !== null;
}

/**
 * Get current account info
 */
export function getAccount() {
  return currentAccount;
}
