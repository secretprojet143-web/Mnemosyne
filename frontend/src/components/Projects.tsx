import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api';

export default function Projects() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getProjects()
      .then(res => { setProjects(res.projects || []); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const createProject = async () => {
    const title = prompt('Project name:');
    if (!title) return;
    try {
      const newProject = await api.createProject(title);
      setProjects([newProject, ...projects]);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Workspaces</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Manage your AI workspaces and execution contexts.</p>
        </div>
        <button onClick={createProject} className="btn btn-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Workspace
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <svg className="spin" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--neon-blue)" strokeWidth="2" strokeDasharray="16 10" strokeLinecap="round"><circle cx="12" cy="12" r="10"/></svg>
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--neon-error)' }}>{error}</div>
      ) : projects.length === 0 ? (
        <div className="glass" style={{ textAlign: 'center', padding: 60, borderRadius: 'var(--radius-lg)' }}>
          <div style={{ width: 64, height: 64, margin: '0 auto 20px', borderRadius: '50%', background: 'var(--neon-blue-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--neon-blue)" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          </div>
          <h3 style={{ fontSize: 18, marginBottom: 8 }}>No workspaces yet</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 20 }}>Create your first workspace to get started.</p>
          <button onClick={createProject} className="btn btn-primary">Create Workspace</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
          <AnimatePresence>
            {projects.map((p, i) => (
              <motion.div key={p.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                whileHover={{ y: -4 }}
                className="glass card-hover"
                style={{ borderRadius: 'var(--radius-lg)', padding: 24, cursor: 'pointer', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg, var(--neon-blue), var(--neon-purple))' }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 'var(--radius-md)', background: 'var(--neon-blue-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--neon-blue)" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                  </div>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 600 }}>{p.title}</h3>
                    <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>ID: {p.id}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="badge badge-blue">ACTIVE</span>
                  <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                    {p.updated_at ? new Date(p.updated_at).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
