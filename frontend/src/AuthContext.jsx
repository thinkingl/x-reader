import React, { createContext, useContext, useState, useEffect } from 'react';
import api from './api';

const AuthContext = createContext(null);

// Pure JS SHA-256 implementation (works in non-secure contexts)
async function sha256(message) {
  const msgUint8 = new TextEncoder().encode(message);
  // Use js-sha256 or implement manually - fallback to Web Crypto if available
  if (window.crypto?.subtle) {
    try {
      const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
      return Array.from(new Uint8Array(hashBuffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
    } catch (e) {
      // Fall through to manual implementation
    }
  }
  // Manual SHA-256
  return sha256Manual(msgUint8);
}

async function hmacSha256(key, message) {
  if (window.crypto?.subtle) {
    try {
      const keyObj = await crypto.subtle.importKey(
        'raw', new TextEncoder().encode(key),
        { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
      );
      const sig = await crypto.subtle.sign('HMAC', keyObj, new TextEncoder().encode(message));
      return Array.from(new Uint8Array(sig))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
    } catch (e) {
      // Fall through
    }
  }
  return hmacSha256Manual(key, message);
}

// Manual SHA-256 for non-secure contexts
function sha256Manual(data) {
  const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  
  const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  
  const bytes = data instanceof Uint8Array ? data : new TextEncoder().encode(data);
  const bitLen = bytes.length * 8;
  
  // Padding
  const padded = new Uint8Array(Math.ceil((bytes.length + 9) / 64) * 64);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  view.setUint32(padded.length - 4, bitLen, false);
  
  // Process blocks
  for (let offset = 0; offset < padded.length; offset += 64) {
    const w = new Uint32Array(64);
    for (let i = 0; i < 16; i++) {
      w[i] = view.getUint32(offset + i * 4, false);
    }
    for (let i = 16; i < 64; i++) {
      const s0 = (w[i-15] >>> 7 | w[i-15] << 25) ^ (w[i-15] >>> 18 | w[i-15] << 14) ^ (w[i-15] >>> 3);
      const s1 = (w[i-2] >>> 17 | w[i-2] << 15) ^ (w[i-2] >>> 19 | w[i-2] << 13) ^ (w[i-2] >>> 10);
      w[i] = (w[i-16] + s0 + w[i-7] + s1) >>> 0;
    }
    
    let [a, b, c, d, e, f, g, h] = H;
    
    for (let i = 0; i < 64; i++) {
      const S1 = (e >>> 6 | e << 26) ^ (e >>> 11 | e << 21) ^ (e >>> 25 | e << 7);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
      const S0 = (a >>> 2 | a << 30) ^ (a >>> 13 | a << 19) ^ (a >>> 22 | a << 10);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      
      h = g; g = f; f = e;
      e = (d + temp1) >>> 0;
      d = c; c = b; b = a;
      a = (temp1 + temp2) >>> 0;
    }
    
    H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
    H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
  }
  
  return H.map(h => h.toString(16).padStart(8, '0')).join('');
}

function hmacSha256Manual(key, message) {
  const blockSize = 64;
  const keyBytes = new TextEncoder().encode(key);
  const msgBytes = new TextEncoder().encode(message);
  
  let k = keyBytes;
  if (k.length > blockSize) {
    k = hexToBytes(sha256Manual(k));
  }
  if (k.length < blockSize) {
    const padded = new Uint8Array(blockSize);
    padded.set(k);
    k = padded;
  }
  
  const ipad = new Uint8Array(blockSize);
  const opad = new Uint8Array(blockSize);
  for (let i = 0; i < blockSize; i++) {
    ipad[i] = k[i] ^ 0x36;
    opad[i] = k[i] ^ 0x5c;
  }
  
  const inner = new Uint8Array(blockSize + msgBytes.length);
  inner.set(ipad);
  inner.set(msgBytes, blockSize);
  const innerHash = hexToBytes(sha256Manual(inner));
  
  const outer = new Uint8Array(blockSize + 32);
  outer.set(opad);
  outer.set(innerHash, blockSize);
  
  return sha256Manual(outer);
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

export function AuthProvider({ children }) {
  const [isAuthEnabled, setIsAuthEnabled] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
    const savedToken = localStorage.getItem('auth_token');
    if (savedToken) {
      setToken(savedToken);
      setIsAuthenticated(true);
      api.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
    }
  }, []);

  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401 && isAuthEnabled) {
          logout();
        }
        return Promise.reject(error);
      }
    );
    return () => api.interceptors.response.eject(interceptor);
  }, [isAuthEnabled]);

  const checkAuthStatus = async () => {
    try {
      const response = await api.get('/api/auth/status');
      setIsAuthEnabled(response.data.enabled);
      setLoading(false);
    } catch (error) {
      setLoading(false);
    }
  };

  const login = async (authKey) => {
    try {
      const challengeRes = await api.post('/api/auth/challenge');
      const { nonce, timestamp, salt } = challengeRes.data;

      const keyHash = await sha256(salt + authKey);
      const response = await hmacSha256(keyHash, nonce + timestamp);

      const verifyRes = await api.post('/api/auth/verify', {
        response,
        timestamp,
      });

      if (verifyRes.data.success) {
        const newToken = verifyRes.data.token;
        setToken(newToken);
        setIsAuthenticated(true);
        localStorage.setItem('auth_token', newToken);
        api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
        return { success: true };
      }
      return { success: false, message: verifyRes.data.message };
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || '登录失败' };
    }
  };

  const enableAuth = async (authKey) => {
    try {
      const salt = Array.from(crypto.getRandomValues(new Uint8Array(16)))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');

      const keyHash = await sha256(salt + authKey);

      const response = await api.post('/api/auth/enable', {
        key_hash: keyHash,
        key_salt: salt,
      });

      if (response.data.success) {
        setIsAuthEnabled(true);
        await login(authKey);
        return { success: true };
      }
      return { success: false, message: response.data.message };
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || '启用认证失败' };
    }
  };

  const disableAuth = async (authKey) => {
    try {
      const challengeRes = await api.post('/api/auth/challenge');
      const { nonce, timestamp, salt } = challengeRes.data;

      const keyHash = await sha256(salt + authKey);
      const response = await hmacSha256(keyHash, nonce + timestamp);

      const verifyRes = await api.post('/api/auth/disable', {
        response,
        timestamp,
      });

      if (verifyRes.data.success) {
        setIsAuthEnabled(false);
        setIsAuthenticated(false);
        setToken(null);
        localStorage.removeItem('auth_token');
        delete api.defaults.headers.common['Authorization'];
        return { success: true };
      }
      return { success: false, message: verifyRes.data.message };
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || '停用认证失败' };
    }
  };

  const logout = () => {
    setToken(null);
    setIsAuthenticated(false);
    localStorage.removeItem('auth_token');
    delete api.defaults.headers.common['Authorization'];
  };

  const value = {
    isAuthEnabled,
    isAuthenticated,
    loading,
    login,
    logout,
    enableAuth,
    disableAuth,
    checkAuthStatus,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
