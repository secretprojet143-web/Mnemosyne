import { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      className="glass" style={{ borderRadius: 'var(--radius-lg)', padding: 24, marginBottom: 16 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
        {title}
      </h3>
      {children}
    </motion.div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--glass-border)' }}>
      <span style={{ fontSize: 14 }}>{label}</span>
      <button onClick={() => onChange(!value)}
        style={{
          width: 44, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer', position: 'relative',
          background: value ? 'var(--neon-blue)' : 'rgba(255,255,255,0.1)',
          transition: 'background 0.3s',
        }}>
        <div style={{
          width: 18, height: 18, borderRadius: '50%', background: '#fff',
          position: 'absolute', top: 3, left: value ? 23 : 3,
          transition: 'left 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
        }} />
      </button>
    </div>
  );
}

function RadioGroup({ label, options, value, onChange }: { label: string; options: { value: string; label: string; desc: string }[]; value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: 0.5, textTransform: 'uppercase', marginBottom: 12 }}>{label}</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {options.map(opt => (
          <button key={opt.value} onClick={() => onChange(opt.value)}
            className={value === opt.value ? 'btn btn-primary' : 'btn btn-secondary'}
            style={{ padding: '10px 20px', fontSize: 13, flexDirection: 'column', gap: 2 }}>
            <span>{opt.label}</span>
            <span style={{ fontSize: 10, opacity: 0.7 }}>{opt.desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Settings() {
  const { user, logout } = useAuth();
  const [chatMode, setChatMode] = useState('standard');
  const [retrievalMode, setRetrievalMode] = useState('balanced');
  const [initiativeMode, setInitiativeMode] = useState('balanced');
  const [autoConsolidate, setAutoConsolidate] = useState(true);

  return (
    <div style={{ padding: 24, maxWidth: 720 }}>
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Settings</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Configure your Mnemosyne AI workspace.</p>
      </div>

      <Section title="Operator Profile">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 'var(--radius-lg)',
            background: 'linear-gradient(135deg, var(--neon-blue), var(--neon-purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22, fontWeight: 700, color: '#fff',
            boxShadow: 'var(--shadow-glow-blue)',
          }}>
            {user?.charAt(0).toUpperCase() || '?'}
          </div>
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 600 }}>{user || 'Unknown'}</h3>
            <p style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>ROLE: OPERATOR &bull; PLAN: PRO</p>
          </div>
        </div>
      </Section>

      <Section title="AI Configuration">
        <RadioGroup label="Chat Mode"
          value={chatMode} onChange={setChatMode}
          options={[
            { value: 'fast', label: 'Fast', desc: 'Quick responses' },
            { value: 'standard', label: 'Standard', desc: 'Balanced' },
            { value: 'deep', label: 'Deep', desc: 'Thorough analysis' },
          ]} />
        <RadioGroup label="Retrieval Mode"
          value={retrievalMode} onChange={setRetrievalMode}
          options={[
            { value: 'balanced', label: 'Balanced', desc: 'Mixed retrieval' },
            { value: 'deep_memory', label: 'Deep Memory', desc: 'Prioritize memories' },
            { value: 'focused', label: 'Focused', desc: 'Targeted search' },
            { value: 'document_first', label: 'Docs First', desc: 'Document priority' },
          ]} />
        <RadioGroup label="Initiative Mode"
          value={initiativeMode} onChange={setInitiativeMode}
          options={[
            { value: 'quiet', label: 'Quiet', desc: 'Minimal suggestions' },
            { value: 'balanced', label: 'Balanced', desc: 'Moderate help' },
            { value: 'active', label: 'Active', desc: 'Frequent suggestions' },
            { value: 'coach', label: 'Coach', desc: 'Full guidance' },
          ]} />
      </Section>

      <Section title="System">
        <Toggle label="Auto-consolidation" value={autoConsolidate} onChange={setAutoConsolidate} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0' }}>
          <span style={{ fontSize: 14 }}>API Endpoint</span>
          <span style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>http://localhost:8000</span>
        </div>
      </Section>

      <Section title="Danger Zone">
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn btn-danger" onClick={logout}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Sign Out
          </button>
        </div>
      </Section>

      <div style={{ textAlign: 'center', padding: '24px 0', fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
        Mnemosyne AI v3.0.0 &bull; Build 2026.03.24
      </div>
    </div>
  );
}
