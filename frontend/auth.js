/**
 * Authentication Module for Globle Club
 * Phone-only login (no OTP), persistent JWT, and guest UUID tracking
 */

// Configuration - Use same API_BASE_URL from app.js
const AUTH_TOKEN_KEY = 'globle_auth_token';
const AUTH_USER_KEY = 'globle_auth_user';
const GUEST_UUID_KEY = 'globle_guest_uuid';

// Global auth state
let currentAuthUser = null;
let authToken = null;

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize authentication on page load
 */
async function initAuth() {
    // Load token from localStorage
    authToken = localStorage.getItem(AUTH_TOKEN_KEY);
    
    if (authToken) {
        // Verify token is still valid
        const user = await verifyToken();
        if (user) {
            currentAuthUser = user;
            updateAuthUI(true);
        } else {
            // Do not clear token on transient failures; keep and show logged-out UI
            updateAuthUI(false);
        }
    } else {
        updateAuthUI(false);
    }
    
    // Check session limit on page load
    await checkSessionLimit();
}

/**
 * Verify token with backend
 */
async function verifyToken() {
    if (!authToken) return null;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const user = await response.json();
            localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
            return user;
        } else if (response.status === 401) {
            return null; // invalid token
        } else {
            // Keep last known user on non-401 errors
            const cached = localStorage.getItem(AUTH_USER_KEY);
            return cached ? JSON.parse(cached) : null;
        }
    } catch (error) {
        console.error('Token verification failed:', error);
        const cached = localStorage.getItem(AUTH_USER_KEY);
        return cached ? JSON.parse(cached) : null;
    }
}

// ============================================================================
// Session Tracking
// ============================================================================

/**
 * Check if user can start a new search session
 */
async function checkSessionLimit() {
    try {
        const headers = {};
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        } else {
            const guestId = getOrCreateGuestId();
            if (guestId) headers['X-Guest-Id'] = guestId;
        }
        
        const response = await fetch(`${API_BASE_URL}/auth/check-session-limit`, {
            headers
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Update UI with session info
            updateSessionInfo(data);
            
            // If cannot search, show login modal
            if (!data.can_search && data.requires_auth) {
                showLoginModal(data.message);
                return false;
            }
            
            return data.can_search;
        }
    } catch (error) {
        console.error('Failed to check session limit:', error);
    }
    
    return true; // Allow search on error (fail open)
}

/**
 * Track session start
 */
async function trackSessionStart(sessionId, searchType, searchInput) {
    try {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        } else {
            const guestId = getGuestId();
            if (guestId) headers['X-Guest-Id'] = guestId;
        }
        const body = {
            session_id: sessionId,
            search_type: searchType,
            search_input: searchInput
        };
        const guestId = getGuestId();
        if (!authToken && guestId) body['guest_uuid'] = guestId;

        await fetch(`${API_BASE_URL}/auth/track-session`, {
            method: 'POST',
            headers,
            body: JSON.stringify(body)
        });
    } catch (error) {
        console.error('Failed to track session:', error);
    }
}

/**
 * Mark session as complete
 */
async function completeSession(sessionId) {
    try {
        const headers = {};
        if (!authToken) {
            const guestId = getGuestId();
            if (guestId) headers['X-Guest-Id'] = guestId;
        }
        await fetch(`${API_BASE_URL}/auth/complete-session?session_id=${sessionId}`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Failed to complete session:', error);
    }
}

// ============================================================================
// Authentication Flow
// ============================================================================

// Phone-only login
async function loginPhone(phoneNumber) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login-phone`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ phone_number: phoneNumber })
        });
        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            localStorage.setItem(AUTH_TOKEN_KEY, authToken);
            const user = await verifyToken();
            currentAuthUser = user;
            return { success: true, user };
        } else {
            const error = await response.json().catch(() => ({}));
            return { success: false, message: error.detail || 'Login failed' };
        }
    } catch (e) {
        return { success: false, message: 'Network error. Please try again.' };
    }
}

/**
 * Logout user
 */
async function logout() {
    try {
        if (authToken) {
            await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        clearAuth();
        updateAuthUI(false);
        // Reload page to reset state
        window.location.reload();
    }
}

/**
 * Clear authentication data
 */
function clearAuth() {
    authToken = null;
    currentAuthUser = null;
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
}

// ============================================================================
// UI Functions
// ============================================================================

/**
 * Show login modal
 */
function showLoginModal(message = null) {
    const modal = document.getElementById('auth-modal');
    const messageEl = document.getElementById('auth-modal-message');
    
    if (message) {
        messageEl.textContent = message;
        messageEl.classList.remove('hidden');
    } else {
        messageEl.classList.add('hidden');
    }
    
    // Reset to phone input screen
    showPhoneInputScreen();
    
    modal.classList.remove('hidden');
}

/**
 * Hide login modal
 */
function hideLoginModal() {
    const modal = document.getElementById('auth-modal');
    modal.classList.add('hidden');
    
    // Reset form
    document.getElementById('phone-number-input').value = '';
    clearPhoneError();
}

/**
 * Show phone input screen
 */
function showPhoneInputScreen() {
    document.getElementById('phone-input-screen').classList.remove('hidden');
}

/**
 * Show OTP input screen
 */
function showOTPInputScreen() {
    document.getElementById('phone-input-screen').classList.add('hidden');
    document.getElementById('otp-input-screen').classList.remove('hidden');
    
    // Focus on OTP input
    document.getElementById('otp-input').focus();
    
    // Start resend timer
    startResendTimer();
}

/**
 * Handle phone number submission
 */
async function handlePhoneSubmit() {
    const phoneInput = document.getElementById('phone-number-input');
    const phoneNumber = phoneInput.value.trim();
    
    // Validate phone number
    if (!phoneNumber) {
        showPhoneError('Please enter your phone number');
        return;
    }
    
    // Format phone number (+91 + 10 digits)
    let formattedPhone = phoneNumber;
    if (!phoneNumber.startsWith('+')) {
        if (phoneNumber.length === 10) {
            formattedPhone = '+91' + phoneNumber;
        } else {
            showPhoneError('Invalid phone number format');
            return;
        }
    }
    
    clearPhoneError();
    showPhoneLoading(true);
    
    const result = await loginPhone(formattedPhone);
    showPhoneLoading(false);
    if (result.success) {
        updateAuthUI(true);
        hideLoginModal();
        alert('Logged in successfully');
        await checkSessionLimit();
    } else {
        showPhoneError(result.message || 'Login failed');
    }
}

/**
 * Handle OTP verification
 */
// Continue as Guest
function continueAsGuest() {
    getOrCreateGuestId();
    hideLoginModal();
}

/**
 * Resend OTP
 */
async function resendOTP() {
    const phoneNumber = document.getElementById('phone-input-screen').dataset.phoneNumber;
    
    if (!phoneNumber) {
        showOTPError('Phone number not found. Please go back.');
        return;
    }
    
    showOTPLoading(true);
    
    const result = await sendOTP(phoneNumber);
    
    showOTPLoading(false);
    
    if (result.success) {
        showOTPSuccess('✅ OTP sent again!');
        startResendTimer();
    } else {
        showOTPError(result.message);
    }
}

/**
 * Start resend timer (60 seconds)
 */
// OTP resend removed

/**
 * Update authentication UI
 */
function updateAuthUI(isAuthenticated) {
    const authButton = document.getElementById('auth-button');
    const userInfo = document.getElementById('user-info');
    
    if (isAuthenticated && currentAuthUser) {
        // Show user info
        if (authButton) authButton.classList.add('hidden');
        if (userInfo) userInfo.classList.remove('hidden');
        
        // Format phone number for display
        const phone = currentAuthUser.phone_number;
        const displayPhone = phone.slice(-10).replace(/(\d{5})(\d{5})/, '$1-$2');
        const phoneDisplay = document.getElementById('user-phone-display');
        if (phoneDisplay) phoneDisplay.textContent = displayPhone;
    } else {
        // Show login button
        if (authButton) authButton.classList.remove('hidden');
        if (userInfo) userInfo.classList.add('hidden');
    }
}

/**
 * Update session info display
 */
function updateSessionInfo(data) {
    const sessionInfo = document.getElementById('session-info');
    
    if (!sessionInfo) return;
    
    if (data.sessions_remaining > 0 && !currentAuthUser) {
        sessionInfo.textContent = `${data.sessions_remaining} free search${data.sessions_remaining !== 1 ? 'es' : ''} remaining`;
        sessionInfo.classList.remove('hidden');
    } else {
        sessionInfo.classList.add('hidden');
    }
}

// Helper functions for UI feedback
function showPhoneError(message) {
    const errorEl = document.getElementById('phone-error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }
}

function clearPhoneError() {
    const errorEl = document.getElementById('phone-error');
    if (errorEl) errorEl.classList.add('hidden');
}

function showPhoneLoading(show) {
    const btn = document.getElementById('login-phone-btn');
    const spinner = document.getElementById('phone-loading-spinner');
    
    if (btn) btn.disabled = show;
    if (spinner) {
        if (show) {
            spinner.classList.remove('hidden');
        } else {
            spinner.classList.add('hidden');
        }
    }
}

function showOTPError(message) {
    const errorEl = document.getElementById('otp-error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }
    
    // Clear success message
    const successEl = document.getElementById('otp-success');
    if (successEl) successEl.classList.add('hidden');
}

function clearOTPError() {
    const errorEl = document.getElementById('otp-error');
    if (errorEl) errorEl.classList.add('hidden');
}

function showOTPSuccess(message) {
    const successEl = document.getElementById('otp-success');
    if (successEl) {
        successEl.textContent = message;
        successEl.classList.remove('hidden');
    }
    
    // Clear error message
    const errorEl = document.getElementById('otp-error');
    if (errorEl) errorEl.classList.add('hidden');
}

function showOTPLoading(show) {
    const btn = document.getElementById('verify-otp-btn');
    const spinner = document.getElementById('otp-loading-spinner');
    
    if (btn) btn.disabled = show;
    if (spinner) {
        if (show) {
            spinner.classList.remove('hidden');
        } else {
            spinner.classList.add('hidden');
        }
    }
}

// Initialize auth when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
});

// Guest helpers
function getGuestId() {
    try { return sessionStorage.getItem(GUEST_UUID_KEY); } catch (e) { return null; }
}

function getOrCreateGuestId() {
    let id = getGuestId();
    if (!id && window.crypto && window.crypto.randomUUID) {
        id = window.crypto.randomUUID();
        try { sessionStorage.setItem(GUEST_UUID_KEY, id); } catch (e) {}
    }
    return id;
}
