/* ═══════════════════════════════════════════════════════════════════════════
   AgentPlaceholder — "Coming Soon" panel with example questions
   ═══════════════════════════════════════════════════════════════════════════ */
import './AgentPlaceholder.css';

const EXAMPLE_QUESTIONS = [
  'Why did solids spike on Jan 15?',
  'Compare shaker performance across this job',
  'What caused the mud weight increase?',
];

export default function AgentPlaceholder() {
  return (
    <div className="panel agent-ph animate-in">
      <div className="panel__header">
        <h3 className="panel__title">AI Agent</h3>
        <span className="agent-ph__badge">Coming Soon</span>
      </div>
      <div className="panel__body">
        <p className="agent-ph__desc">
          Ask questions about solids control performance and get AI-powered analysis.
        </p>
        <div className="agent-ph__examples">
          {EXAMPLE_QUESTIONS.map((q, i) => (
            <button key={i} className="agent-ph__pill" disabled>
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
