/* ═══════════════════════════════════════════════════════════════════════════
   EventCards — expandable insight cards with severity badges
   ═══════════════════════════════════════════════════════════════════════════ */
import { useState } from 'react';
import type { InsightItem, TimelineDay } from '../services/insightsApi';
import EventSparkline from './EventSparkline';
import './EventCards.css';

interface Props {
  insights: InsightItem[];
  summary: string;
  timeline: TimelineDay[];
  selectedDate: string | null;
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls = severity === 'high' ? 'badge--high' : severity === 'medium' ? 'badge--medium' : 'badge--low';
  return <span className={`badge ${cls}`}>{severity}</span>;
}

function EventCard({ insight, index, timeline, selectedDate }: {
  insight: InsightItem;
  index: number;
  timeline: TimelineDay[];
  selectedDate: string | null;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`event-card event-card--${insight.severity}`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <button
        className="event-card__header"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <SeverityBadge severity={insight.severity} />
        <span className="event-card__title">{insight.title}</span>
        <svg
          className={`event-card__chevron ${expanded ? 'event-card__chevron--open' : ''}`}
          width="14" height="14" viewBox="0 0 14 14" fill="none"
        >
          <path d="M3.5 5.5L7 9L10.5 5.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {expanded && (
        <div className="event-card__body">
          <p className="event-card__narrative">{insight.narrative}</p>

          {insight.event_type && selectedDate && timeline.length > 0 && (
            <EventSparkline
              eventType={insight.event_type}
              eventValues={insight.values}
              timeline={timeline}
              selectedDate={selectedDate}
            />
          )}

          {insight.cause && (
            <div className="event-card__cause">
              <span className="event-card__cause-label">Cause</span>
              <span className="event-card__cause-text">{insight.cause}</span>
            </div>
          )}
          <div className="event-card__rec">
            <span className="event-card__rec-label">Recommendation</span>
            <span className="event-card__rec-text">{insight.recommendation}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EventCards({ insights, summary, timeline, selectedDate }: Props) {
  if (!insights.length) {
    return (
      <div className="panel event-cards animate-in">
        <div className="panel__header">
          <h3 className="panel__title">Insights</h3>
        </div>
        <div className="panel__body">
          <p className="event-cards__summary">{summary || 'Normal operations — no events detected.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="panel event-cards animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Insights</h3>
        <span className="event-cards__count">{insights.length} event{insights.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="panel__body">
        {summary && <p className="event-cards__summary">{summary}</p>}
        <div className="event-cards__list">
          {insights.map((insight, idx) => (
            <EventCard
              key={idx}
              insight={insight}
              index={idx}
              timeline={timeline}
              selectedDate={selectedDate}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
