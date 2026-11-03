/**
 * classics/auth.js — 고전 디지털 도서관 보안 접속 인증 게이트
 * Password Protection: 2026_acupoint (SHA-256 Hash Verification)
 */
(function() {
  'use strict';

  // SHA-256 hash of "2026_acupoint"
  const AUTH_CONFIG = {
    hash: 'db5d526f50a2951e81159b802a70a860085e8bd8a8bc0f35159e56af323e783d',
    plainFallback: '2026_acupoint',
    sessionKey: 'classics_auth_hash',
    localKey: 'classics_auth_hash',
    expiryKey: 'classics_auth_expiry',
    durationDays: 30
  };

  // Check whether current user is authenticated
  function isAuthenticated() {
    try {
      const s = sessionStorage.getItem(AUTH_CONFIG.sessionKey);
      if (s === AUTH_CONFIG.hash) return true;

      const l = localStorage.getItem(AUTH_CONFIG.localKey);
      const exp = localStorage.getItem(AUTH_CONFIG.expiryKey);
      if (l === AUTH_CONFIG.hash) {
        if (!exp || parseInt(exp, 10) > Date.now()) {
          sessionStorage.setItem(AUTH_CONFIG.sessionKey, AUTH_CONFIG.hash);
          return true;
        } else {
          localStorage.removeItem(AUTH_CONFIG.localKey);
          localStorage.removeItem(AUTH_CONFIG.expiryKey);
        }
      }
    } catch (e) {
      // Storage access blocked or restricted
    }
    return false;
  }

  // SHA-256 helper via Web Crypto API
  async function computeSHA256(text) {
    if (window.crypto && crypto.subtle) {
      try {
        const msgUint8 = new TextEncoder().encode(text);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      } catch (err) {
        return null;
      }
    }
    return null;
  }

  // Determine whether current script is running on portal (index.html)
  const isPortal = (document.currentScript && document.currentScript.getAttribute('data-portal') === 'true') ||
                   (document.documentElement && document.documentElement.getAttribute('data-page') === 'portal');

  // 1. SUBPAGE GUARD: If on a subpage and NOT authenticated, block and redirect to index.html
  if (!isPortal) {
    if (!isAuthenticated()) {
      if (document.documentElement) {
        document.documentElement.style.display = 'none';
      }
      const pathParts = window.location.pathname.replace(/\\/g, '/').split('/').filter(Boolean);
      let targetIndex = 'index.html';
      let returnPath = '';
      
      const currentFile = pathParts.length > 0 ? pathParts[pathParts.length - 1] : '';
      const isSubdir = (pathParts.length > 2) || (pathParts.length === 2 && !currentFile.endsWith('.html'));
      
      if (isSubdir) {
        targetIndex = '../index.html';
        returnPath = encodeURIComponent(pathParts.slice(-2).join('/') + window.location.search);
      } else {
        targetIndex = 'index.html';
        returnPath = encodeURIComponent(currentFile + window.location.search);
      }
      
      window.location.replace(targetIndex + '?return=' + returnPath);
      return;
    }
    // Authenticated on subpage: allow rendering normally
    return;
  }

  // 2. PORTAL (index.html) LOGIC
  // Run early check: if not authenticated, add lock class to prevent content flash
  if (!isAuthenticated()) {
    document.documentElement.classList.add('auth-locked');
  }

  // DOMContentLoaded: attach events and verify UI state
  function setupPortalAuth() {
    const overlay = document.getElementById('auth-overlay');
    const form = document.getElementById('auth-form');
    const pwInput = document.getElementById('auth-password');
    const rememberBox = document.getElementById('auth-remember');
    const errEl = document.getElementById('auth-error');
    const errMsg = document.getElementById('auth-error-msg');
    const submitBtn = document.getElementById('auth-submit-btn');

    if (isAuthenticated()) {
      document.documentElement.classList.remove('auth-locked');
      if (overlay) {
        overlay.classList.add('unlocked');
        overlay.style.display = 'none';
      }
    } else {
      document.documentElement.classList.add('auth-locked');
      if (overlay) {
        overlay.style.display = 'flex';
        overlay.classList.remove('unlocked');
      }
      if (pwInput) {
        setTimeout(() => pwInput.focus(), 150);
      }
    }

    if (form) {
      form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const value = pwInput ? pwInput.value.trim() : '';
        if (!value) {
          showError('열람 비밀번호를 입력해 주세요.');
          return;
        }

        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add('loading');
        }

        const inputHash = await computeSHA256(value);
        const isValid = (inputHash === AUTH_CONFIG.hash) || (value === AUTH_CONFIG.plainFallback);

        if (isValid) {
          try {
            sessionStorage.setItem(AUTH_CONFIG.sessionKey, AUTH_CONFIG.hash);
            if (rememberBox && rememberBox.checked) {
              const expiry = Date.now() + (AUTH_CONFIG.durationDays * 24 * 60 * 60 * 1000);
              localStorage.setItem(AUTH_CONFIG.localKey, AUTH_CONFIG.hash);
              localStorage.setItem(AUTH_CONFIG.expiryKey, expiry.toString());
            }
          } catch (err) {}

          // Unlock
          document.documentElement.classList.remove('auth-locked');
          if (overlay) {
            overlay.classList.add('unlocked');
            setTimeout(() => {
              overlay.style.display = 'none';
            }, 350);
          }

          // Check redirect/return param
          const params = new URLSearchParams(window.location.search);
          const returnUrl = params.get('return') || params.get('redirect');
          if (returnUrl) {
            try {
              const decoded = decodeURIComponent(returnUrl);
              if (!decoded.startsWith('http://') && !decoded.startsWith('https://') && !decoded.startsWith('//')) {
                window.location.replace(decoded);
                return;
              }
            } catch (err) {}
          }
        } else {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('loading');
          }
          showError('비밀번호가 일치하지 않습니다. 다시 확인해 주세요.');
          const card = document.querySelector('.auth-card');
          if (card) {
            card.classList.remove('shake');
            void card.offsetWidth;
            card.classList.add('shake');
          }
          if (pwInput) {
            pwInput.select();
            pwInput.focus();
          }
        }
      });
    }

    function showError(msg) {
      if (errEl && errMsg) {
        errMsg.textContent = msg;
        errEl.style.display = 'flex';
      }
    }
  }

  // Global functions for inline HTML calls
  window.lockLibrary = function() {
    try {
      sessionStorage.removeItem(AUTH_CONFIG.sessionKey);
      localStorage.removeItem(AUTH_CONFIG.localKey);
      localStorage.removeItem(AUTH_CONFIG.expiryKey);
    } catch (e) {}
    document.documentElement.classList.add('auth-locked');
    const overlay = document.getElementById('auth-overlay');
    if (overlay) {
      overlay.style.display = 'flex';
      overlay.classList.remove('unlocked');
    }
    const pwInput = document.getElementById('auth-password');
    if (pwInput) {
      pwInput.value = '';
      setTimeout(() => pwInput.focus(), 150);
    }
    const errEl = document.getElementById('auth-error');
    if (errEl) errEl.style.display = 'none';
  };

  window.togglePasswordVisibility = function() {
    const pwInput = document.getElementById('auth-password');
    const toggleBtn = document.querySelector('.auth-pw-toggle');
    if (!pwInput || !toggleBtn) return;
    if (pwInput.type === 'password') {
      pwInput.type = 'text';
      toggleBtn.textContent = '🙈';
    } else {
      pwInput.type = 'password';
      toggleBtn.textContent = '👁️';
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupPortalAuth);
  } else {
    setupPortalAuth();
  }
})();

