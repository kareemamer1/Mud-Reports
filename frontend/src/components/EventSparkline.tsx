/* ═══════════════════════════════════════════════════════════════════════════
   EventSparkline — inline SVG sparkline for event parameter trends
   Shows ±3 days around the selected date, highlighting the current day.
   ═══════════════════════════════════════════════════════════════════════════ */
import { useMemo, useState, useCallback, useRef } from 'react';
import type { TimelineDay } from '../services/insightsApi';

const HALF_WINDOW = 3; // ±3 days = 7-day window
const W = 260;
const H = 44;
const PAD_X = 4;
const PAD_Y = 6;
const PAD_TOP = 3;
const PAD_BOT = 3;

interface TrendPoint {
  date: string;
  value: number | null;
}

type Extractor = { label: string; unit: string; extract: (d: TimelineDay) => number | null };

/* ── Helper: find equipment hours by name in a timeline day ───────────── */
function _shakerHours(d: TimelineDay, name: string): number | null {
  const s = d.equipment?.shakers?.find(
    (sh: { name: string; hours: number }) => sh.name === name,
  );
  return s?.hours ?? null;
}

function _centrifugeHours(d: TimelineDay, name: string): number | null {
  const c = d.equipment?.centrifuges?.find(
    (ct: { name: string; hours: number }) => ct.name === name,
  );
  return c?.hours ?? null;
}

function _hydroHours(d: TimelineDay, unit: string): number | null {
  const hydro = d.equipment?.hydrocyclones as Record<string, { hours: number }> | undefined;
  return hydro?.[unit]?.hours ?? null;
}

/** Static extractors for mud-property events */
const MUD_EXTRACTORS: Record<string, Extractor[]> = {
  solids_spike:      [{ label: 'Solids', unit: '%', extract: d => d.mud_properties?.solids ?? null }],
  sand_increase:     [{ label: 'Sand', unit: '%', extract: d => d.mud_properties?.sand ?? null }],
  lgs_creep:         [{ label: 'LGS', unit: '%', extract: d => d.mud_properties?.lgs ?? null }],
  drill_solids_rise: [{ label: 'Drill Solids', unit: '%', extract: d => d.mud_properties?.drill_solids ?? null }],
  rheology_shift:    [
    { label: 'PV', unit: 'cP', extract: d => d.mud_properties?.pv ?? null },
    { label: 'YP', unit: 'lb', extract: d => d.mud_properties?.yp ?? null },
  ],
  weight_up:         [{ label: 'MW', unit: 'ppg', extract: d => d.mud_properties?.mud_weight ?? null }],
  dilution:          [{ label: 'MW', unit: 'ppg', extract: d => d.mud_properties?.mud_weight ?? null }],
  ph_shift:          [{ label: 'pH', unit: '', extract: d => d.mud_properties?.ph ?? null }],
};

/** Build extractors dynamically for equipment events using values from the insight */
function getExtractors(eventType: string, values?: Record<string, unknown>): Extractor[] | null {
  // Mud property events — static mapping
  if (MUD_EXTRACTORS[eventType]) return MUD_EXTRACTORS[eventType];

  // Equipment events — need the specific equipment name from values
  const equipName = (values?.shaker ?? values?.centrifuge ?? values?.equipment ?? '') as string;
  const unitName = (values?.unit ?? '') as string;

  switch (eventType) {
    case 'shaker_down':
    case 'screen_change':
    case 'equipment_startup':
      if (equipName) {
        return [{ label: equipName, unit: 'hrs', extract: d => _shakerHours(d, equipName) }];
      }
      break;
    case 'centrifuge_down':
    case 'centrifuge_feed_change':
      if (equipName) {
        return [{ label: equipName, unit: 'hrs', extract: d => _centrifugeHours(d, equipName) }];
      }
      break;
    case 'hydrocyclone_down':
      if (unitName) {
        return [{
          label: unitName.replace('_', ' '),
          unit: 'hrs',
          extract: d => _hydroHours(d, unitName),
        }];
      }
      break;
  }

  return null;
}

interface Props {
  eventType: string;
  eventValues?: Record<string, unknown>;
  timeline: TimelineDay[];
  selectedDate: string;
}

/** Format number for display: integers as-is, decimals to 2 places */
function fmt(v: number): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}

function SingleSparkline({ points, currentIdx, label, unit, color }: {
  points: TrendPoint[];
  currentIdx: number;
  label: string;
  unit: string;
  color: string;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const validPoints = points.map((p, i) => ({ ...p, i })).filter(p => p.value !== null) as { date: string; value: number; i: number }[];

  const onMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const xPct = (e.clientX - rect.left) / rect.width;
    const idx = Math.round(xPct * (points.length - 1));
    setHoverIdx(Math.max(0, Math.min(points.length - 1, idx)));
  }, [points.length]);

  const onMouseLeave = useCallback(() => setHoverIdx(null), []);

  if (validPoints.length < 2) return null;

  const min = Math.min(...validPoints.map(p => p.value));
  const max = Math.max(...validPoints.map(p => p.value));
  const range = max - min || 1;

  const xScale = (i: number) => PAD_X + (i / (points.length - 1)) * (W - PAD_X * 2);
  const yScale = (v: number) => PAD_TOP + PAD_Y + ((max - v) / range) * (H - PAD_Y * 2 - PAD_TOP - PAD_BOT);

  // Build path
  const pathParts = validPoints.map((p, idx) => {
    const x = xScale(p.i);
    const y = yScale(p.value);
    return `${idx === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
  });

  // Area fill — close to chart bottom
  const chartBottom = yScale(min);
  const firstX = xScale(validPoints[0].i);
  const lastX = xScale(validPoints[validPoints.length - 1].i);
  const areaPath = `${pathParts.join(' ')} L${lastX.toFixed(1)},${chartBottom.toFixed(1)} L${firstX.toFixed(1)},${chartBottom.toFixed(1)} Z`;

  // Active index: hover overrides the static current-day marker
  const activeIdx = hoverIdx ?? currentIdx;
  const activePoint = points[activeIdx];
  const hasActiveValue = activePoint?.value !== null && activePoint?.value !== undefined;
  const ax = xScale(activeIdx);
  const ay = hasActiveValue ? yScale(activePoint.value as number) : 0;
  const activeVal = hasActiveValue ? (activePoint.value as number) : null;

  return (
    <div className="event-sparkline__series">
      {/* Header: param name + active value */}
      <div className="event-sparkline__label-row">
        <span className="event-sparkline__param-name" style={{ color }}>{label}</span>
        <span className="event-sparkline__value" style={{ color }}>
          {activeVal !== null ? `${fmt(activeVal)} ${unit}` : `— ${unit}`}
        </span>
      </div>

      {/* Chart */}
      <svg
        ref={svgRef}
        className="event-sparkline__svg"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        onMouseMove={onMouseMove}
        onMouseLeave={onMouseLeave}
      >
        {/* Area fill */}
        <path d={areaPath} fill={color} fillOpacity="0.06" />

        {/* Line */}
        <path
          d={pathParts.join(' ')}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Cursor: vertical line tracks hover or sits on current day */}
        <line
          x1={ax} y1={0}
          x2={ax} y2={H}
          stroke={hoverIdx !== null ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.3)'}
          strokeWidth="1"
          strokeDasharray="3,2"
        />

        {/* Active dot */}
        {hasActiveValue && (
          <>
            <circle cx={ax} cy={ay} r="3" fill={color} fillOpacity="0.3" />
            <circle cx={ax} cy={ay} r="1.5" fill={color} />
          </>
        )}

        {/* Invisible hit-area to catch mouse events across full chart */}
        <rect x="0" y="0" width={W} height={H} fill="transparent" />
      </svg>

      {/* Date labels */}
      <div className="event-sparkline__dates">
        <span>{points[0]?.date.slice(5)}</span>
        <span>{activePoint?.date.slice(5)}</span>
        <span>{points[points.length - 1]?.date.slice(5)}</span>
      </div>
    </div>
  );
}

const SERIES_COLORS = ['#00d4ff', '#f59e0b', '#10b981', '#f43f5e'];

export default function EventSparkline({ eventType, eventValues, timeline, selectedDate }: Props) {
  const extractors = useMemo(
    () => getExtractors(eventType, eventValues),
    [eventType, eventValues],
  );

  const { windowDays, currentIdx } = useMemo(() => {
    const dateIdx = timeline.findIndex(d => d.date === selectedDate);
    if (dateIdx < 0) return { windowDays: [] as TimelineDay[], currentIdx: -1 };

    const start = Math.max(0, dateIdx - HALF_WINDOW);
    const end = Math.min(timeline.length - 1, dateIdx + HALF_WINDOW);
    const days = timeline.slice(start, end + 1);
    const curIdx = dateIdx - start;

    return { windowDays: days, currentIdx: curIdx };
  }, [timeline, selectedDate]);

  if (!extractors || windowDays.length < 2 || currentIdx < 0) return null;

  return (
    <div className="event-sparkline">
      {extractors.map((ext, i) => {
        const points: TrendPoint[] = windowDays.map(d => ({
          date: d.date,
          value: ext.extract(d),
        }));
        return (
          <SingleSparkline
            key={ext.label}
            points={points}
            currentIdx={currentIdx}
            label={ext.label}
            unit={ext.unit}
            color={SERIES_COLORS[i % SERIES_COLORS.length]}
          />
        );
      })}
    </div>
  );
}
