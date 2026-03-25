import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';

const pageVariants = {
  initial: { opacity: 0, scale: 0.98 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: "easeOut" } },
  exit: { opacity: 0, scale: 0.98, transition: { duration: 0.3 } },
} as const;

export default function Auth() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const data = isLogin
        ? await api.login(username, password)
        : await api.register(username, password);
      login(data.access_token);
      navigate('/app', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit"
      style={{ minHeight: '100vh', background: 'var(--bg-void)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>

      {/* Background effects */}
      <div className="grid-bg" style={{ position: 'absolute', inset: 0, opacity: 0.3 }} />
      <div style={{ position: 'absolute', top: '20%', left: '15%', width: 400, height: 400, background: 'radial-gradient(circle, rgba(59,130,246,0.1) 0%, transparent 70%)', filter: 'blur(60px)', animation: 'float-slow 8s ease-in-out infinite' }} />
      <div style={{ position: 'absolute', bottom: '20%', right: '15%', width: 350, height: 350, background: 'radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 70%)', filter: 'blur(60px)', animation: 'float-slow 10s ease-in-out infinite 2s' }} />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
        className="glass"
        style={{ width: 420, padding: '48px 40px', borderRadius: 'var(--radius-xl)', position: 'relative', zIndex: 10, overflow: 'hidden' }}>

        {/* Top shine */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: 'linear-gradient(90deg, transparent, rgba(139,92,246,0.5), transparent)' }} />

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'linear-gradient(135deg, var(--neon-blue), var(--neon-purple))', boxShadow: '0 0 12px rgba(59,130,246,0.5)' }} />
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 700, letterSpacing: 1 }}>Mnemosyne</span>
        </div>

        <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
          {isLogin ? 'Welcome back' : 'Create account'}
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 32 }}>
          {isLogin ? 'Authenticate to access your AI workspace.' : 'Register a new operator account.'}
        </p>

        {error && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
            style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 'var(--radius-md)', padding: '12px 16px', marginBottom: 20, fontSize: 13, color: '#fca5a5' }}>
            {error}
          </motion.div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontFamily: 'var(--font-mono)', letterSpacing: 0.5 }}>USERNAME</label>
            <input className="input-field" type="text" placeholder="operator_name" value={username} onChange={e => setUsername(e.target.value)} required autoComplete="username" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontFamily: 'var(--font-mono)', letterSpacing: 0.5 }}>ACCESS CODE</label>
            <input className="input-field" type="password" placeholder="Enter access code" value={password} onChange={e => setPassword(e.target.value)} required autoComplete={isLogin ? 'current-password' : 'new-password'} />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isLoading} style={{ marginTop: 8, padding: '14px 24px', fontSize: 15, width: '100%' }}>
            {isLoading ? (
              <svg className="spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeDasharray="16 10" strokeLinecap="round"><circle cx="12" cy="12" r="10"/></svg>
            ) : (
              isLogin ? 'Access System' : 'Register Operator'
            )}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <button onClick={() => { setIsLogin(!isLogin); setError(''); }} className="btn btn-ghost" style={{ fontSize: 13 }}>
            {isLogin ? "Need an account? Register" : "Already registered? Sign in"}
          </button>
        </div>

        <button onClick={() => navigate('/')} className="btn btn-ghost" style={{ fontSize: 12, marginTop: 16, width: '100%', color: 'var(--text-dim)' }}>
          &larr; Back to homepage
        </button>
      </motion.div>
    </motion.div>
  );
}
