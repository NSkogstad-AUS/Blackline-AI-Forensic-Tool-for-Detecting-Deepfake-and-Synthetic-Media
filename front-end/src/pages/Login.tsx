import React, { useEffect, useState } from 'react';
import './Login.css';
import { getAuthState, subscribe, login as doLogin, signup as doSignup } from '../state/authStore';

interface LoginProps {
  // Optional hint: where the user was trying to go
  targetPage?: string;
}

const Login: React.FC<LoginProps> = ({ targetPage }) => {
  const [auth, setAuth] = useState(getAuthState());
  useEffect(() => { const unsub = subscribe(setAuth); return () => { unsub(); }; }, []);

  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAuth(action: 'login' | 'signup') {
    setPending(true); setError(null);
    try {
      if (!form.username || !form.password || (action==='signup' && !form.email)) {
        setError('Please fill all required fields');
        setPending(false);
        return;
      }
      if (action === 'login') {
        await doLogin(form.username, form.password);
      } else {
        await doSignup(form.username, form.email, form.password);
      }
    } catch (e: any) {
      setError(e.message || 'Failed');
    } finally { setPending(false); }
  }

  const heading = auth.user ? 'Welcome back' : (mode==='login' ? 'Sign in' : 'Create your account');
  return (
    <div className="login-page" role="main">
      <div className="login-card" aria-live="polite">
        <h1>{heading}</h1>
        {targetPage && (
          <div className="login-note">Access to <strong>{targetPage}</strong> requires an account.</div>
        )}
        <div className="login-toggle">
          <button className={`lp-btn small ${mode==='login' ? 'primary' : ''}`} onClick={()=>setMode('login')}>Login</button>
          <button className={`lp-btn small ${mode==='signup' ? 'primary' : ''}`} onClick={()=>setMode('signup')}>Sign up</button>
        </div>
        <form className="login-form" onSubmit={(e)=>{ e.preventDefault(); handleAuth(mode); }}>
          <label className="lp-field">Username
            <input required value={form.username} onChange={e=>setForm(f=>({...f, username:e.target.value}))} />
          </label>
          {mode==='signup' && (
            <label className="lp-field">Email
              <input required type="email" value={form.email} onChange={e=>setForm(f=>({...f, email:e.target.value}))} />
            </label>
          )}
          <label className="lp-field">Password
            <input required type="password" value={form.password} onChange={e=>setForm(f=>({...f, password:e.target.value}))} />
          </label>
          {error && <div className="lp-error" role="alert">{error}</div>}
          {auth.error && !error && <div className="lp-error" role="alert">{auth.error}</div>}
          <button className="lp-btn primary wide" disabled={pending}>{pending ? (mode==='login' ? 'Logging in…' : 'Creating…') : (mode==='login' ? 'Login' : 'Create Account')}</button>
        </form>
      </div>
    </div>
  );
};

export default Login;
