import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../api';

function BarChart({ data, maxVal }: { data: { label: string; value: number; color: string }[]; maxVal: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 120, padding: '0 4px' }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: `${Math.max((d.value / Math.max(maxVal, 1)) * 100, 2)}%` }}
            transition={{ duration: 0.8, delay: i * 0.1, ease: "easeOut" }}
            style={{
              width: '100%', maxWidth: 36, borderRadius: '6px 6px 2px 2px',
              background: `linear-gradient(180deg, ${d.color}, ${d.color}80)`,
              boxShadow: `0 0 12px ${d.color}40`,
              minHeight: 4,
            }}
          />
          <span style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{d.label}</span>
        </div>
      ))}
    </div>
  );
}

function StatCard({ label, value, color, delay }: { label: string; value: string | number; color: string; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="glass"
      style={{ padding: 24, borderRadius: 'var(--radius-lg)', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: color }} />
      <p style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', letterSpacing: 1, marginBottom: 8 }}>{label}</p>
      <span style={{ fontSize: 32, fontWeight: 700, fontFamily: 'var(--font-display)', color }}>{value}</span>
    </motion.div>
  );
}

export default function Stats() {
  const [stats, setStats] = useState<any>(null);
  const [temporal, setTemporal] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, temporalRes] = await Promise.all([
          api.getFullStats().catch(() => null),
          api.getTemporalHealth().catch(() => null),
        ]);
        setStats(statsRes);
        setTemporal(temporalRes);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <svg className="spin" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--neon-blue)" strokeWidth="2" strokeDasharray="16 10" strokeLinecap="round"><circle cx="12" cy="12" r="10"/></svg>
      </div>
    );
  }

  const memory = stats?.memory || {};
  const continuity = stats?.continuity || {};
  const temporalCounts = stats?.temporal || temporal?.counts || {};

  const categoryData = [
    { label: 'Facts', value: memory.facts || 0, color: 'var(--neon-blue)' },
    { label: 'Convos', value: memory.conversations || 0, color: 'var(--neon-purple)' },
    { label: 'Messages', value: memory.messages || 0, color: 'var(--neon-cyan)' },
    { label: 'Projects', value: continuity.active_projects || 0, color: 'var(--neon-emerald)' },
    { label: 'Goals', value: continuity.active_goals || 0, color: 'var(--neon-amber)' },
    { label: 'Loops', value: continuity.open_loops || 0, color: 'var(--neon-rose)' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Analytics</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>System performance metrics and memory analytics.</p>
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Active Facts" value={memory.active_facts || 0} color="var(--neon-blue)" delay={0} />
        <StatCard label="Conversations" value={memory.conversations || 0} color="var(--neon-purple)" delay={0.05} />
        <StatCard label="Messages" value={memory.messages || 0} color="var(--neon-cyan)" delay={0.1} />
        <StatCard label="Projects" value={continuity.active_projects || 0} color="var(--neon-emerald)" delay={0.15} />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 32 }}>
        <div className="glass" style={{ borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 20 }}>Memory Distribution</h3>
          <BarChart data={categoryData} maxVal={Math.max(...categoryData.map(d => d.value), 1)} />
        </div>
        <div className="glass" style={{ borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 20 }}>Health</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { label: 'Stale Facts', value: temporalCounts.stale_facts || 0, color: 'var(--neon-amber)' },
              { label: 'Aging Goals', value: temporalCounts.aging_goals || 0, color: 'var(--neon-rose)' },
              { label: 'Aging Loops', value: temporalCounts.aging_open_loops || 0, color: 'var(--neon-error)' },
            ].map((item, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item.label}</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: item.value > 0 ? item.color : 'var(--neon-emerald)' }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Temporal Health Details */}
      {(temporal?.stale_facts?.length > 0 || temporal?.aging_goals?.length > 0) && (
        <div className="glass" style={{ borderRadius: 'var(--radius-lg)' }}>
          <div className="panel-header"><h2>Items Needing Attention</h2></div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {temporal.aging_goals?.slice(0, 5).map((g: any, i: number) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(244,63,94,0.04)', border: '1px solid rgba(244,63,94,0.1)' }}>
                <span style={{ color: 'var(--neon-rose)', fontSize: 10 }}>◆</span>
                <span style={{ fontSize: 13, flex: 1 }}>{g.goal_text}</span>
                <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{g.age_days}d</span>
              </div>
            ))}
            {temporal.aging_open_loops?.slice(0, 5).map((l: any, i: number) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.1)' }}>
                <span style={{ color: 'var(--neon-error)', fontSize: 10 }}>◆</span>
                <span style={{ fontSize: 13, flex: 1 }}>{l.description}</span>
                <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{l.age_days}d</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
