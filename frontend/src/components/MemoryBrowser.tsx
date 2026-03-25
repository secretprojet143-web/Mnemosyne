import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../api';

const categoryColors: Record<string, string> = {
  identity: 'var(--neon-purple)',
  preference: 'var(--neon-blue)',
  project: 'var(--neon-cyan)',
  skill: 'var(--neon-emerald)',
  goal: 'var(--neon-amber)',
  location: 'var(--neon-rose)',
  work: 'var(--neon-blue)',
  general: 'var(--text-muted)',
};

export default function MemoryBrowser() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [selectedMemory, setSelectedMemory] = useState<number | null>(null);
  const [facts, setFacts] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [factsRes, statsRes] = await Promise.all([
          api.getFacts().catch(() => ({ facts: [], total: 0 })),
          api.getMemoryStats().catch(() => null),
        ]);
        setFacts(factsRes.facts || []);
        setStats(statsRes);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const categories = ['all', ...new Set(facts.map(m => m.category))];

  const filtered = facts.filter(m => {
    const matchSearch = !searchQuery || m.fact_text.toLowerCase().includes(searchQuery.toLowerCase());
    const matchCategory = filterCategory === 'all' || m.category === filterCategory;
    return matchSearch && matchCategory;
  });

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Memory Browser</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Browse persistent memories extracted by the AI.</p>
      </div>

      {/* Search & Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <div className="input-group" style={{ flex: 1, minWidth: 240 }}>
          <span className="input-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </span>
          <input className="input-field" type="text" placeholder="Search memories..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {categories.map(cat => (
            <button key={cat} onClick={() => setFilterCategory(cat)}
              className={`btn ${filterCategory === cat ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '8px 16px', fontSize: 12, textTransform: 'capitalize' }}>
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Total Facts', value: stats.facts || 0, color: 'var(--neon-blue)' },
            { label: 'Active', value: stats.active_facts || 0, color: 'var(--neon-emerald)' },
            { label: 'Conversations', value: stats.conversations || 0, color: 'var(--neon-purple)' },
            { label: 'Messages', value: stats.messages || 0, color: 'var(--neon-amber)' },
          ].map((s, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass"
              style={{ padding: 16, borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <p style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', letterSpacing: 1, marginBottom: 4 }}>{s.label}</p>
              <p style={{ fontSize: 24, fontWeight: 700, fontFamily: 'var(--font-display)', color: s.color }}>{s.value}</p>
            </motion.div>
          ))}
        </div>
      )}

      {/* Memory List */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <svg className="spin" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--neon-blue)" strokeWidth="2" strokeDasharray="16 10" strokeLinecap="round"><circle cx="12" cy="12" r="10"/></svg>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((m, i) => (
            <motion.div key={m.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              onClick={() => setSelectedMemory(selectedMemory === m.id ? null : m.id)}
              className="glass card-hover"
              style={{ borderRadius: 'var(--radius-md)', padding: '16px 20px', cursor: 'pointer', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: categoryColors[m.category] || 'var(--neon-blue)' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 14, marginBottom: 8 }}>{m.fact_text}</p>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    <span className="badge" style={{ background: `${categoryColors[m.category] || 'var(--text-muted)'}15`, color: categoryColors[m.category] || 'var(--text-muted)', borderColor: `${categoryColors[m.category] || 'var(--text-muted)'}40` }}>
                      {m.category}
                    </span>
                    <span className={`badge badge-${m.status === 'active' ? 'emerald' : 'amber'}`}>{m.status}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      conf: {((m.confidence || 0) * 100).toFixed(0)}%
                    </span>
                    {m.is_pinned && <span className="badge badge-purple">pinned</span>}
                  </div>
                </div>
                <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                  {m.created_at ? new Date(m.created_at).toLocaleDateString() : ''}
                </span>
              </div>
            </motion.div>
          ))}

          {filtered.length === 0 && !loading && (
            <div className="glass" style={{ textAlign: 'center', padding: 48, borderRadius: 'var(--radius-lg)' }}>
              <p style={{ color: 'var(--text-dim)', fontSize: 14 }}>
                {facts.length === 0 ? 'No memories yet. Chat with the AI to start creating memories.' : 'No memories match your search.'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
