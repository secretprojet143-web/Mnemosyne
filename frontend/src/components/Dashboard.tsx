import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api';

interface Intelligence {
  step_title?: string;
  step_description?: string;
  step_order?: number;
  step_id?: number;
  confidence?: number;
  risk?: string;
  prediction?: string | null;
  known_solution?: string | null;
  known_count?: number;
  project_insight?: string | null;
  plan_title?: string;
  plan_id?: number;
  sample_size?: number;
  next_action?: string;
  progress?: { total_steps: number; completed: number; in_progress: number; pending: number } | null;
}

interface ChatMessage {
  sender: string;
  text: string;
  time: string;
  intelligence?: Intelligence | null;
}

function getImpactTranslation(prediction: string, risk: string): string {
  if (risk === 'high') {
    return 'High risk — this step could cause issues if not handled carefully. Double-check before proceeding.';
  }
  if (prediction.includes('40%') || prediction.includes('42%') || prediction.includes('50%') || prediction.includes('60%')) {
    return 'This means there\'s a high chance this step will fail without careful validation.';
  }
  if (prediction.includes('20%') || prediction.includes('retries')) {
    return 'Similar steps have needed extra attempts before. Budget time for troubleshooting.';
  }
  return 'Based on past patterns, this step may need attention.';
}

function IntelligencePanel({ intel }: { intel: Intelligence }) {
  const [expanded, setExpanded] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState(false);

  if (!intel.step_title) return null;

  const handleFeedback = async (outcome: string) => {
    if (feedbackSent || !intel.plan_id || !intel.step_id) return;
    setFeedback(outcome);
    setFeedbackSent(true);
    try {
      await api.submitFeedback(intel.plan_id, intel.step_id, outcome);
    } catch {
      // silent fail
    }
  };

  const confidencePct = Math.round((intel.confidence || 0.5) * 100);
  const riskColors: Record<string, string> = { low: '#22c55e', medium: '#eab308', high: '#ef4444' };
  const riskIcons: Record<string, string> = { low: '🟢', medium: '🟡', high: '🔴' };
  const riskColor = riskColors[intel.risk || 'medium'] || '#eab308';
  const riskIcon = riskIcons[intel.risk || 'medium'] || '⚪';
  const hasLearningData = (intel.sample_size || 0) >= 3;

  return (
    <motion.div
      initial={{ opacity: 0, y: -12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="intel-panel"
      style={{
        background: 'rgba(0,0,0,0.35)',
        border: '1px solid rgba(59,130,246,0.2)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        fontSize: 12,
        fontFamily: 'var(--font-mono)',
      }}
    >
      {/* Header — always visible */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '10px 14px', cursor: 'pointer',
          background: 'rgba(59,130,246,0.06)',
          borderBottom: expanded ? '1px solid rgba(59,130,246,0.1)' : 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--neon-blue)', fontWeight: 700, fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.5 }}>
            {expanded ? '▾' : '▸'} Execution
          </span>
          {intel.plan_title && (
            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{intel.plan_title}</span>
          )}
          {/* Learning Badge */}
          {hasLearningData && (
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 }}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                padding: '2px 8px', borderRadius: 10,
                background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)',
                fontSize: 9, color: 'var(--neon-blue)', fontWeight: 600,
              }}
            >
              🧠 Learned from {intel.sample_size} executions
            </motion.span>
          )}
        </div>
        {intel.progress && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 50, height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${intel.progress.total_steps > 0 ? (intel.progress.completed / intel.progress.total_steps * 100) : 0}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
                style={{ height: '100%', borderRadius: 2, background: 'var(--neon-blue)' }}
              />
            </div>
            <span style={{ color: 'var(--text-dim)', fontSize: 10 }}>
              {intel.progress.completed}/{intel.progress.total_steps}
            </span>
          </div>
        )}
      </div>

      {/* Expanded Body */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {/* Current Step */}
              <div style={{ padding: '8px 10px', background: 'rgba(59,130,246,0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(59,130,246,0.15)' }}>
                <span style={{ color: 'var(--neon-blue)', fontSize: 10, fontWeight: 700, letterSpacing: 1 }}>STEP {intel.step_order}</span>
                <div style={{ color: 'var(--text-primary)', fontWeight: 600, marginTop: 2, fontFamily: 'var(--font-body)', fontSize: 13 }}>
                  {intel.step_title}
                </div>
              </div>

              {/* Confidence + Risk */}
              <div style={{ display: 'flex', gap: 20, padding: '4px 0' }}>
                <div>
                  <span style={{ color: 'var(--text-dim)', fontSize: 9, textTransform: 'uppercase', letterSpacing: 1 }}>Confidence</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                    <ConfidenceBar value={intel.confidence || 0.5} />
                    <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{confidencePct}%</span>
                  </div>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)', fontSize: 9, textTransform: 'uppercase', letterSpacing: 1 }}>Risk</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 3 }}>
                    <span>{riskIcon}</span>
                    <span style={{ color: riskColor, fontWeight: 600 }}>{intel.risk}</span>
                  </div>
                </div>
              </div>

              {/* Prediction + WHY THIS MATTERS */}
              {intel.prediction && (
                <motion.div
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                  style={{
                    padding: '8px 10px',
                    background: 'rgba(234,179,8,0.08)', borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(234,179,8,0.2)',
                  }}
                >
                  <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#eab308' }}>
                    ⚠ Prediction
                  </span>
                  <div style={{ marginTop: 4, color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', fontSize: 12, lineHeight: 1.5 }}>
                    {intel.prediction}
                  </div>
                  <div style={{ marginTop: 6, padding: '5px 8px', background: 'rgba(234,179,8,0.06)', borderRadius: 'var(--radius-sm)', fontSize: 11, color: '#ca8a04', fontFamily: 'var(--font-body)' }}>
                    → {getImpactTranslation(intel.prediction, intel.risk || 'medium')}
                  </div>
                </motion.div>
              )}

              {/* Known Solution */}
              {intel.known_solution && (
                <motion.div
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  style={{
                    padding: '8px 10px',
                    background: 'rgba(34,197,94,0.08)', borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(34,197,94,0.2)',
                  }}
                >
                  <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#22c55e' }}>
                    💡 Known Solution ({intel.known_count}x used)
                  </span>
                  <div style={{ marginTop: 4, color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', fontSize: 12 }}>
                    {intel.known_solution}
                  </div>
                </motion.div>
              )}

              {/* Project Insight */}
              {intel.project_insight && (
                <motion.div
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                  style={{
                    padding: '8px 10px',
                    background: 'rgba(168,85,247,0.08)', borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(168,85,247,0.2)',
                  }}
                >
                  <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#a855f7' }}>
                    🔮 Project Insight
                  </span>
                  <div style={{ marginTop: 4, color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', fontSize: 12, lineHeight: 1.5 }}>
                    {intel.project_insight}
                  </div>
                </motion.div>
              )}

              {/* Next Action */}
              {intel.next_action && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  style={{
                    padding: '8px 10px', marginTop: 2,
                    background: 'rgba(59,130,246,0.1)', borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(59,130,246,0.2)',
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                  }}
                >
                  <span style={{ color: 'var(--neon-blue)', fontSize: 13, lineHeight: 1, flexShrink: 0 }}>→</span>
                  <div>
                    <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--neon-blue)' }}>
                      Next Action
                    </span>
                    <div style={{ marginTop: 3, color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', fontSize: 12, lineHeight: 1.5 }}>
                      {intel.next_action}
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Outcome Feedback */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                style={{
                  padding: '10px 12px', marginTop: 4,
                  background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-dim)' }}>
                  Outcome
                </span>
                {feedbackSent ? (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    style={{ marginTop: 6, fontSize: 12, color: feedback === 'success' ? '#22c55e' : feedback === 'partial' ? '#eab308' : '#ef4444', fontFamily: 'var(--font-body)' }}
                  >
                    {feedback === 'success' ? '✅ Recorded — this strengthens future predictions.' :
                     feedback === 'partial' ? '⚠️ Noted — I\'ll adjust confidence for similar steps.' :
                     '❌ Logged — I\'ll adapt the strategy for next time.'}
                  </motion.div>
                ) : (
                  <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                    {[
                      { key: 'success', label: '✅ Yes', color: 'rgba(34,197,94,0.15)', border: 'rgba(34,197,94,0.3)', text: '#22c55e' },
                      { key: 'partial', label: '⚠️ Partially', color: 'rgba(234,179,8,0.15)', border: 'rgba(234,179,8,0.3)', text: '#eab308' },
                      { key: 'failure', label: '❌ No', color: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.3)', text: '#ef4444' },
                    ].map(btn => (
                      <button
                        key={btn.key}
                        onClick={() => handleFeedback(btn.key)}
                        style={{
                          padding: '5px 12px', borderRadius: 'var(--radius-sm)',
                          background: btn.color, border: `1px solid ${btn.border}`,
                          color: btn.text, fontSize: 11, fontWeight: 600,
                          cursor: 'pointer', fontFamily: 'var(--font-mono)',
                          transition: 'transform 0.15s ease',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.05)')}
                        onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
                      >
                        {btn.label}
                      </button>
                    ))}
                  </div>
                )}
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const filled = Math.round(value * 5);
  return (
    <div style={{ display: 'flex', gap: 3 }}>
      {[0, 1, 2, 3, 4].map(i => (
        <motion.div
          key={i}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.05 * i, duration: 0.2 }}
          style={{
            width: 8, height: 8, borderRadius: '50%',
            background: i < filled ? 'var(--neon-blue)' : 'rgba(255,255,255,0.1)',
            boxShadow: i < filled ? '0 0 4px rgba(59,130,246,0.5)' : 'none',
          }}
        />
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [chatInput, setChatInput] = useState('');
  const [chatLog, setChatLog] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [goals, setGoals] = useState<any[]>([]);
  const [openLoops, setOpenLoops] = useState<any[]>([]);
  const [briefing, setBriefing] = useState<any>(null);
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdFiles, setCreatedFiles] = useState<string[]>([]);
  const [learningInsights, setLearningInsights] = useState<any>(null);
  const [milestone, setMilestone] = useState<any>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatLog, isThinking, isStreaming]);

  const loadData = async () => {
    try {
      const [projRes, goalRes, loopRes, briefingRes, statsRes, learnRes] = await Promise.all([
        api.getProjects().catch(() => ({ projects: [] })),
        api.getGoals().catch(() => ({ goals: [] })),
        api.getOpenLoops().catch(() => ({ open_loops: [] })),
        api.getProactiveBriefing().catch(() => null),
        api.getMemoryStats().catch(() => null),
        api.getLearningInsights().catch(() => null),
      ]);
      setProjects(projRes.projects || []);
      setGoals(goalRes.goals || []);
      setOpenLoops(loopRes.open_loops || []);
      setBriefing(briefingRes);
      setMemoryStats(statsRes);
      setLearningInsights(learnRes);
      setError(null);
    } catch (e: any) {
      console.error('Load error:', e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Detect milestone from learning insights
  useEffect(() => {
    if (learningInsights?.user_impact?.milestone) {
      const m = learningInsights.user_impact.milestone;
      // Check localStorage to avoid re-showing same milestone
      const shown = localStorage.getItem(`milestone_${m.key}`);
      if (!shown) {
        setMilestone(m);
        localStorage.setItem(`milestone_${m.key}`, '1');
        // Auto-dismiss after 8 seconds
        setTimeout(() => setMilestone(null), 8000);
      }
    }
  }, [learningInsights]);

  const handleSend = async (overrideMsg?: string) => {
    const msg = (overrideMsg || chatInput).trim();
    if (!msg) return;
    setChatInput('');
    setChatLog(prev => [...prev, { sender: 'user', text: msg, time: new Date().toLocaleTimeString() }]);
    setIsThinking(true);
    try {
      // Store facts from user message
      await api.storeFacts(msg).catch(() => {});

      // Add empty system message that will be filled token-by-token
      setChatLog(prev => [...prev, { sender: 'system', text: '', time: new Date().toLocaleTimeString() }]);
      setIsThinking(false);
      setIsStreaming(true);

      // Stream tokens
      await api.chatWithMemoryStream(
        msg,
        (token: string) => {
          setChatLog(prev => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.sender === 'system') {
              updated[updated.length - 1] = { ...last, text: last.text + token };
            }
            return updated;
          });
        },
        (files: string[]) => {
          setCreatedFiles(prev => [...prev, ...files]);
        },
        (meta: Intelligence) => {
          // Attach intelligence metadata to the last system message
          setChatLog(prev => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.sender === 'system') {
              updated[updated.length - 1] = { ...last, intelligence: meta };
            }
            return updated;
          });
        },
      );

      // Refresh all data
      await loadData();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsThinking(false);
      setIsStreaming(false);
    }
  };

  const createProject = async () => {
    const title = prompt('Project name:');
    if (!title) return;
    try {
      await api.createProject(title);
      const res = await api.getProjects();
      setProjects(res.projects || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const status = (isThinking || isStreaming) ? 1 : (openLoops.length > 0 ? 2 : 0);
  const nextActions = briefing?.top_priorities || [];
  const briefingLines = briefing?.briefing_lines || [];

  return (
    <div style={{ display: 'flex', height: '100%', gap: 20, padding: 20 }}>
      {/* Chat Panel */}
      <div className="glass panel" style={{ flex: 1, minWidth: 0 }}>
        <div className="panel-header">
          <h2>AI Terminal</h2>
          <div className="badge" style={{
            background: status === 0 ? 'var(--neon-emerald-dim)' : status === 1 ? 'var(--neon-blue-dim)' : 'var(--neon-purple-dim)',
            color: status === 0 ? 'var(--neon-emerald)' : status === 1 ? 'var(--neon-blue)' : 'var(--neon-purple)',
            borderColor: status === 0 ? 'rgba(16,185,129,0.25)' : status === 1 ? 'rgba(59,130,246,0.25)' : 'rgba(139,92,246,0.25)',
          }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor', boxShadow: `0 0 6px currentColor` }} />
            {status === 0 ? 'IDLE' : status === 1 ? 'PROCESSING' : 'ACTIVE'}
          </div>
        </div>

        <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <AnimatePresence>
            {chatLog.map((msg, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 'var(--radius-md)', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700,
                  background: msg.sender === 'system' ? 'linear-gradient(135deg, var(--neon-blue), var(--neon-purple))' : 'rgba(255,255,255,0.05)',
                  border: msg.sender === 'system' ? 'none' : '1px solid var(--glass-border)',
                  color: msg.sender === 'system' ? '#fff' : 'var(--text-muted)',
                  boxShadow: msg.sender === 'system' ? '0 0 15px rgba(59,130,246,0.3)' : 'none',
                }}>
                  {msg.sender === 'system' ? 'AI' : 'OP'}
                </div>
                <div style={{
                  flex: 1, display: 'flex', flexDirection: 'column', gap: 8,
                }}>
                  {/* Intelligence Panel */}
                  {msg.intelligence && msg.sender === 'system' && (
                    <IntelligencePanel intel={msg.intelligence} />
                  )}

                  {/* Message Body */}
                  <div style={{
                    background: msg.sender === 'system' ? 'rgba(59,130,246,0.04)' : 'rgba(255,255,255,0.02)',
                    border: `1px solid ${msg.sender === 'system' ? 'rgba(59,130,246,0.15)' : 'var(--glass-border)'}`,
                    borderRadius: 'var(--radius-md)', padding: '14px 18px',
                  }}>
                    <p style={{ fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                      {msg.text}
                      {isStreaming && msg.sender === 'system' && i === chatLog.length - 1 && (
                        <span className="streaming-cursor" />
                      )}
                    </p>
                    <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginTop: 6, display: 'block' }}>{msg.time}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {isThinking && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-md)', background: 'linear-gradient(135deg, var(--neon-blue), var(--neon-purple))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#fff' }}>AI</div>
              <div style={{ display: 'flex', gap: 6, padding: '14px 20px' }}>
                {[0, 1, 2].map(i => (
                  <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--neon-blue)', animation: `typing-dots 1.2s ease-in-out infinite`, animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </motion.div>
          )}

          {chatLog.length === 0 && !isThinking && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 'auto' }}>
              <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 1, textTransform: 'uppercase' }}>Try These</span>
              {[
                'Hello, who are you?',
                'What do you remember about me?',
                'What are my current priorities?',
                'My name is Alex and I work at SpaceX'
              ].map((p, i) => (
                <button key={i} onClick={() => handleSend(p)}
                  className="glass-subtle"
                  style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', textAlign: 'left', cursor: 'pointer', border: '1px solid var(--glass-border)', color: 'var(--text-secondary)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10, transition: 'all 0.2s' }}>
                  <span style={{ color: 'var(--neon-blue)', fontWeight: 700, fontSize: 14 }}>&gt;</span>
                  {p}
                </button>
              ))}
            </motion.div>
          )}

          <div ref={chatEndRef} />
        </div>

        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--glass-border)' }}>
          <div style={{ position: 'relative' }}>
            <input className="input-field" type="text" placeholder="Type a message..." value={chatInput}
              onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSend()}
              disabled={isThinking || isStreaming} style={{ paddingRight: 48, background: 'rgba(0,0,0,0.3)' }} />
            <button onClick={() => handleSend()} disabled={isThinking || isStreaming}
              style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--neon-blue)', padding: 4, display: 'flex' }}>
              {isThinking ? (
                <svg className="spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="16 10" strokeLinecap="round"><circle cx="12" cy="12" r="10"/></svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Right column */}
      <div style={{ width: 380, display: 'flex', flexDirection: 'column', gap: 20, flexShrink: 0 }}>
        {/* Proactive Briefing */}
        {briefingLines.length > 0 && (
          <div className="glass panel">
            <div className="panel-header"><h2>Proactive Briefing</h2></div>
            <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {briefingLines.map((line: string, i: number) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <span style={{ color: 'var(--neon-amber)', fontSize: 10, marginTop: 3 }}>◆</span>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{line}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Actions */}
        {nextActions.length > 0 && (
          <div className="glass panel">
            <div className="panel-header"><h2>Next Actions</h2></div>
            <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {nextActions.slice(0, 5).map((action: any, i: number) => (
                <div key={i} className="glass-subtle" style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{action.text}</span>
                  <span className={`badge badge-${action.priority === 'critical' ? 'rose' : action.priority === 'high' ? 'amber' : 'blue'}`}>{action.priority}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Projects */}
        <div className="glass panel" style={{ maxHeight: 200 }}>
          <div className="panel-header">
            <h2>Projects</h2>
            <button onClick={createProject} className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 12px' }}>+ New</button>
          </div>
          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {projects.slice(0, 5).map(p => (
              <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--neon-blue)" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{p.title}</span>
                <span className={`badge badge-${p.priority === 'high' || p.priority === 'critical' ? 'amber' : 'blue'}`} style={{ marginLeft: 'auto' }}>{p.priority}</span>
              </div>
            ))}
            {projects.length === 0 && <div style={{ color: 'var(--text-dim)', fontSize: 13, fontStyle: 'italic', textAlign: 'center', padding: 16 }}>No projects yet</div>}
          </div>
        </div>

        {/* Goals */}
        {goals.length > 0 && (
          <div className="glass panel" style={{ maxHeight: 180 }}>
            <div className="panel-header"><h2>Active Goals</h2></div>
            <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {goals.slice(0, 5).map(g => (
                <div key={g.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px' }}>
                  <span style={{ color: 'var(--neon-emerald)', fontSize: 10 }}>◆</span>
                  <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{g.goal_text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Open Loops */}
        {openLoops.length > 0 && (
          <div className="glass panel" style={{ maxHeight: 180 }}>
            <div className="panel-header"><h2>Open Loops</h2></div>
            <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {openLoops.slice(0, 5).map(l => (
                <div key={l.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px' }}>
                  <span style={{ color: 'var(--neon-rose)', fontSize: 10 }}>◆</span>
                  <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{l.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Memory Stats */}
        {memoryStats && (
          <div className="glass panel" style={{ maxHeight: 140 }}>
            <div className="panel-header"><h2>Memory Stats</h2></div>
            <div className="panel-body" style={{ display: 'flex', gap: 16 }}>
              <div style={{ flex: 1, background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', padding: 16, border: '1px solid var(--glass-border)' }}>
                <p style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', letterSpacing: 1, marginBottom: 4 }}>Facts</p>
                <p style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-display)' }}>{memoryStats.active_facts || 0}</p>
              </div>
              <div style={{ flex: 1, background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', padding: 16, border: '1px solid var(--glass-border)' }}>
                <p style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', letterSpacing: 1, marginBottom: 4 }}>Conversations</p>
                <p style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-display)', color: 'var(--neon-blue)' }}>{memoryStats.conversations || 0}</p>
              </div>
            </div>
          </div>
        )}

        {/* Learning Insights */}
        {learningInsights && (
          <div className="glass panel" style={{ maxHeight: 340 }}>
            <div className="panel-header"><h2>🧠 Learning Insights</h2></div>
            <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {/* Success Rate */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)' }}>
                <div>
                  <p style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', letterSpacing: 1 }}>Success Rate</p>
                  <p style={{ fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-display)', color: 'var(--neon-blue)' }}>{learningInsights.success_rate}%</p>
                </div>
                {learningInsights.success_rate_trend && (
                  <div style={{
                    padding: '4px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
                    fontFamily: 'var(--font-mono)',
                    background: learningInsights.success_rate_trend.direction === 'up' ? 'rgba(34,197,94,0.15)' : learningInsights.success_rate_trend.direction === 'down' ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.05)',
                    color: learningInsights.success_rate_trend.direction === 'up' ? '#22c55e' : learningInsights.success_rate_trend.direction === 'down' ? '#ef4444' : 'var(--text-dim)',
                  }}>
                    {learningInsights.success_rate_trend.direction === 'up' ? '↑' : learningInsights.success_rate_trend.direction === 'down' ? '↓' : '→'}
                    {' '}{learningInsights.success_rate_trend.prior}% → {learningInsights.success_rate_trend.current}%
                  </div>
                )}
              </div>

              {/* Stats Row */}
              <div style={{ display: 'flex', gap: 8 }}>
                <div style={{ flex: 1, padding: '8px 10px', background: 'rgba(34,197,94,0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(34,197,94,0.15)' }}>
                  <p style={{ fontSize: 9, color: '#22c55e', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>Learned</p>
                  <p style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-display)', color: '#22c55e' }}>{learningInsights.total_patterns}</p>
                </div>
                <div style={{ flex: 1, padding: '8px 10px', background: 'rgba(59,130,246,0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(59,130,246,0.15)' }}>
                  <p style={{ fontSize: 9, color: 'var(--neon-blue)', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>This Week</p>
                  <p style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-display)', color: 'var(--neon-blue)' }}>+{learningInsights.new_solutions_week}</p>
                </div>
                <div style={{ flex: 1, padding: '8px 10px', background: 'rgba(168,85,247,0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(168,85,247,0.15)' }}>
                  <p style={{ fontSize: 9, color: '#a855f7', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>Confidence</p>
                  <p style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-display)', color: '#a855f7' }}>{learningInsights.average_confidence}%</p>
                </div>
              </div>

              {/* Top Fix */}
              {learningInsights.top_fix && learningInsights.top_fix.summary && (
                <div style={{ padding: '8px 12px', background: 'rgba(34,197,94,0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(34,197,94,0.15)' }}>
                  <p style={{ fontSize: 9, color: '#22c55e', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>Top Learned Fix</p>
                  <p style={{ fontSize: 12, fontFamily: 'var(--font-body)', color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>
                    {learningInsights.top_fix.summary}
                    <span style={{ color: '#22c55e', fontWeight: 600 }}> (used {learningInsights.top_fix.count}x)</span>
                  </p>
                </div>
              )}

              {/* High Risk Warning */}
              {learningInsights.high_risk_fail_rate > 20 && (
                <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239,68,68,0.15)' }}>
                  <p style={{ fontSize: 9, color: '#ef4444', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>⚠ High-Risk Area</p>
                  <p style={{ fontSize: 12, fontFamily: 'var(--font-body)', color: 'var(--text-secondary)', marginTop: 4 }}>
                    High-risk steps still fail {learningInsights.high_risk_fail_rate}% of the time.
                  </p>
                </div>
              )}

              {/* User Impact */}
              {learningInsights.user_impact && learningInsights.user_impact.feedback_count > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  style={{ padding: '8px 12px', background: 'rgba(234,179,8,0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(234,179,8,0.2)' }}
                >
                  <p style={{ fontSize: 9, color: '#eab308', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>✨ Your Impact</p>
                  <p style={{ fontSize: 12, fontFamily: 'var(--font-body)', color: 'var(--text-secondary)', marginTop: 4 }}>
                    You helped improve success rate by
                    <span style={{ color: '#22c55e', fontWeight: 700 }}> +{learningInsights.user_impact.impact_pct}% </span>
                    this week
                    <span style={{ color: 'var(--text-dim)', fontSize: 10 }}> ({learningInsights.user_impact.feedback_count} feedback{learningInsights.user_impact.feedback_count !== 1 ? 's' : ''})</span>
                  </p>
                </motion.div>
              )}

              {/* Next Milestone Progress */}
              {learningInsights.user_impact?.next_milestone && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.06)' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 9, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>Next Milestone</span>
                    <span style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      {learningInsights.user_impact.next_milestone.current}/{learningInsights.user_impact.next_milestone.target}
                    </span>
                  </div>
                  <div style={{ width: '100%', height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${learningInsights.user_impact.next_milestone.pct}%` }}
                      transition={{ duration: 1, ease: 'easeOut' }}
                      style={{ height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, var(--neon-blue), #a855f7)' }}
                    />
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', marginTop: 6 }}>
                    {learningInsights.user_impact.next_milestone.pct}% to
                    <span style={{ color: '#a855f7', fontWeight: 600 }}> {learningInsights.user_impact.next_milestone.title}</span>
                  </p>
                </motion.div>
              )}
            </div>
          </div>
        )}

        {/* Created Files */}
        {createdFiles.length > 0 && (
          <div className="glass panel" style={{ maxHeight: 160 }}>
            <div className="panel-header">
              <h2>Created Files</h2>
              <button onClick={() => setCreatedFiles([])} className="btn btn-ghost" style={{ fontSize: 11, padding: '2px 8px' }}>Clear</button>
            </div>
            <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {createdFiles.map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--neon-emerald)' }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  data/projects/{f}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            style={{
              position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 100,
              background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)',
              padding: '12px 24px', color: '#fca5a5', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10,
              backdropFilter: 'blur(12px)',
            }}>
            {error}
            <button onClick={() => setError(null)} style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer', marginLeft: 8, fontSize: 16 }}>&times;</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Milestone Celebration Toast */}
      <AnimatePresence>
        {milestone && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.95 }}
            transition={{ type: 'spring', damping: 20 }}
            style={{
              position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 200,
              background: 'linear-gradient(135deg, rgba(234,179,8,0.15), rgba(168,85,247,0.15))',
              border: '1px solid rgba(234,179,8,0.3)',
              borderRadius: 'var(--radius-lg)',
              padding: '16px 28px',
              backdropFilter: 'blur(16px)',
              textAlign: 'center',
              minWidth: 320,
              boxShadow: '0 8px 32px rgba(234,179,8,0.15)',
            }}
          >
            <div style={{ fontSize: 28, marginBottom: 6 }}>🎉</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#eab308', fontFamily: 'var(--font-display)', marginBottom: 4 }}>
              {milestone.title}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', lineHeight: 1.5 }}>
              {milestone.description}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginTop: 8 }}>
              {milestone.count} feedback{milestone.count !== 1 ? 's' : ''} contributed
            </div>
            <button
              onClick={() => setMilestone(null)}
              style={{
                marginTop: 10, padding: '4px 16px', borderRadius: 'var(--radius-sm)',
                background: 'rgba(234,179,8,0.2)', border: '1px solid rgba(234,179,8,0.3)',
                color: '#eab308', fontSize: 11, fontWeight: 600, cursor: 'pointer',
              }}
            >
              ✨ Nice!
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
