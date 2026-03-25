import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';

const pageVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.6, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.3 } },
} as const;

const stagger = {
  animate: { transition: { staggerChildren: 0.12 } },
} as const;

const fadeUp = {
  initial: { opacity: 0, y: 40 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } },
} as const;

function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = canvas.width = window.innerWidth;
    let h = canvas.height = window.innerHeight;

    const particles: { x: number; y: number; vx: number; vy: number; r: number; a: number }[] = [];
    for (let i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 1.5 + 0.5,
        a: Math.random() * 0.5 + 0.1,
      });
    }

    let raf: number;
    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);

      particles.forEach((p, i) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(139, 92, 246, ${p.a})`;
        ctx.fill();

        for (let j = i + 1; j < particles.length; j++) {
          const dx = p.x - particles[j].x;
          const dy = p.y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(59, 130, 246, ${0.06 * (1 - dist / 150)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      });
      raf = requestAnimationFrame(draw);
    }
    draw();

    const resize = () => { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; };
    window.addEventListener('resize', resize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
  }, []);

  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }} />;
}

function FloatingOrb({ color, size, x, y, delay }: { color: string; size: number; x: string; y: string; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 2, delay, ease: 'easeOut' }}
      style={{
        position: 'absolute', left: x, top: y, width: size, height: size,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
        filter: 'blur(40px)',
        animation: `float-slow ${8 + delay}s ease-in-out infinite`,
        animationDelay: `${delay}s`,
        pointerEvents: 'none',
      }}
    />
  );
}

const features = [
  { icon: '01', title: 'Persistent Memory', desc: 'Your AI remembers every conversation, fact, and context across sessions.', color: 'var(--neon-blue)' },
  { icon: '02', title: 'Execution Planning', desc: 'Multi-step reasoning chains with dependency tracking and live progress.', color: 'var(--neon-purple)' },
  { icon: '03', title: 'Document Intelligence', desc: 'Upload documents, search semantically, and get contextual answers.', color: 'var(--neon-cyan)' },
  { icon: '04', title: 'Autonomous Actions', desc: 'Configure initiative modes and let the AI proactively assist you.', color: 'var(--neon-emerald)' },
  { icon: '05', title: 'Temporal Awareness', desc: 'Detect changes over time, track goals, and surface aging items.', color: 'var(--neon-amber)' },
  { icon: '06', title: 'Trust & Security', desc: 'Multi-layer security scanning, prompt injection defense, and access control.', color: 'var(--neon-rose)' },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit"
      style={{ minHeight: '100vh', background: 'var(--bg-void)', position: 'relative', overflow: 'hidden' }}>

      <ParticleField />
      <FloatingOrb color="rgba(59, 130, 246, 0.15)" size={500} x="-10%" y="10%" delay={0} />
      <FloatingOrb color="rgba(139, 92, 246, 0.12)" size={400} x="70%" y="20%" delay={1.5} />
      <FloatingOrb color="rgba(6, 182, 212, 0.08)" size={350} x="50%" y="60%" delay={3} />

      {/* Grid background */}
      <div className="grid-bg" style={{ position: 'absolute', inset: 0, opacity: 0.4, pointerEvents: 'none' }} />

      {/* Nav */}
      <motion.nav initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.8, delay: 0.2 }}
        style={{ position: 'relative', zIndex: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 48px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'linear-gradient(135deg, var(--neon-blue), var(--neon-purple))', boxShadow: '0 0 15px rgba(59,130,246,0.5)' }} />
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700, letterSpacing: 1 }}>Mnemosyne</span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn btn-ghost" onClick={() => navigate('/auth')}>Sign In</button>
          <button className="btn btn-primary" onClick={() => navigate('/auth?register=true')}>Get Started</button>
        </div>
      </motion.nav>

      {/* Hero */}
      <motion.section variants={stagger} initial="initial" animate="animate"
        style={{ position: 'relative', zIndex: 5, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '100px 24px 80px', maxWidth: 900, margin: '0 auto' }}>

        <motion.div variants={fadeUp}
          className="badge badge-purple"
          style={{ marginBottom: 32, padding: '6px 16px', fontSize: 12 }}>
          v3.0 &mdash; Now with Autonomous Execution
        </motion.div>

        <motion.h1 variants={fadeUp}
          style={{ fontSize: 'clamp(40px, 7vw, 80px)', lineHeight: 1.05, marginBottom: 24, fontWeight: 800 }}>
          An AI that<br />
          <span className="text-gradient">Remembers, Plans & Acts.</span>
        </motion.h1>

        <motion.p variants={fadeUp}
          style={{ fontSize: 18, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 600, marginBottom: 48 }}>
          Mnemosyne is a next-generation AI operating system with persistent memory,
          multi-step reasoning, document intelligence, and autonomous execution.
        </motion.p>

        <motion.div variants={fadeUp} style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
          <button className="btn btn-primary" onClick={() => navigate('/auth')}
            style={{ padding: '16px 36px', fontSize: 16 }}>
            Start Free Trial
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
          <button className="btn btn-secondary" style={{ padding: '16px 36px', fontSize: 16 }}>
            View Documentation
          </button>
        </motion.div>

        {/* Animated Orb */}
        <motion.div variants={fadeUp} style={{ marginTop: 80, position: 'relative', width: 300, height: 300 }}>
          <div style={{
            position: 'absolute', inset: 0, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(139,92,246,0.2) 0%, rgba(59,130,246,0.08) 50%, transparent 70%)',
            animation: 'float-slow 6s ease-in-out infinite',
          }}>
            <div style={{
              position: 'absolute', inset: '15%', borderRadius: '50%',
              border: '1px solid rgba(59,130,246,0.2)',
              animation: 'pulse-glow 4s ease-in-out infinite',
            }} />
            <div style={{
              position: 'absolute', inset: '30%', borderRadius: '50%',
              border: '1px solid rgba(139,92,246,0.3)',
              background: 'radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)',
            }} />
          </div>
          {/* Orbiting dots */}
          {[0, 1, 2].map(i => (
            <div key={i} style={{
              position: 'absolute', top: '50%', left: '50%', width: 6, height: 6, marginTop: -3, marginLeft: -3,
              borderRadius: '50%', background: i === 0 ? 'var(--neon-blue)' : i === 1 ? 'var(--neon-purple)' : 'var(--neon-cyan)',
              boxShadow: `0 0 10px ${i === 0 ? 'var(--neon-blue)' : i === 1 ? 'var(--neon-purple)' : 'var(--neon-cyan)'}`,
              animation: `orbit ${6 + i * 2}s linear infinite`,
              animationDelay: `${i * -2}s`,
            }} />
          ))}
        </motion.div>
      </motion.section>

      {/* Features Grid */}
      <motion.section initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: 1 }}
        style={{ position: 'relative', zIndex: 5, padding: '60px 48px 120px', maxWidth: 1200, margin: '0 auto' }}>

        <motion.h2 initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          style={{ textAlign: 'center', fontSize: 14, textTransform: 'uppercase', letterSpacing: 3, color: 'var(--text-muted)', marginBottom: 12, fontFamily: 'var(--font-mono)' }}>
          Core Capabilities
        </motion.h2>
        <motion.p initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          style={{ textAlign: 'center', fontSize: 32, fontWeight: 700, marginBottom: 64 }}>
          Everything you need, <span className="text-gradient">nothing you don't.</span>
        </motion.p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
          {features.map((f, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease: "easeOut" }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              className="glass card-hover"
              style={{ padding: 32, borderRadius: 'var(--radius-lg)', cursor: 'default', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg, transparent, ${f.color}, transparent)`, opacity: 0.5 }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: f.color, fontWeight: 600 }}>{f.icon}</span>
              <h3 style={{ fontSize: 18, marginTop: 12, marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* CTA */}
      <motion.section initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
        style={{ position: 'relative', zIndex: 5, textAlign: 'center', padding: '80px 24px 120px' }}>
        <div className="glass" style={{ maxWidth: 700, margin: '0 auto', padding: '60px 40px', borderRadius: 'var(--radius-xl)', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg, rgba(59,130,246,0.05), rgba(139,92,246,0.05))', pointerEvents: 'none' }} />
          <h2 style={{ fontSize: 36, fontWeight: 700, marginBottom: 16 }}>Ready to build your AI memory?</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 32, fontSize: 16 }}>Join the next generation of AI-assisted workflows.</p>
          <button className="btn btn-primary" onClick={() => navigate('/auth')} style={{ padding: '16px 40px', fontSize: 16 }}>
            Launch Mnemosyne
          </button>
        </div>
      </motion.section>

      {/* Footer */}
      <footer style={{ position: 'relative', zIndex: 5, borderTop: '1px solid var(--glass-border)', padding: '24px 48px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13, color: 'var(--text-dim)' }}>
        <span>&copy; 2026 Mnemosyne AI. All rights reserved.</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>SYS_STATUS: OPERATIONAL</span>
      </footer>
    </motion.div>
  );
}
