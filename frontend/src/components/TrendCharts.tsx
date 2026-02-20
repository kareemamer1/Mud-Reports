/* ═══════════════════════════════════════════════════════════════════════════
   TrendCharts — 4-chart grid showing 7-day rolling trends
   Uses Recharts with dark CFR-style aesthetic
   ═══════════════════════════════════════════════════════════════════════════ */
import { useMemo, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { TimelineDay } from '../services/insightsApi';
import './TrendCharts.css';

interface Props {
  timeline: TimelineDay[];
  selectedDate: string | null;
}

/* ── Shared chart config ──────────────────────────────────────────────── */
const AXIS_STYLE = {
  fontSize: 9,
  fill: 'rgba(255,255,255,0.38)',
  fontFamily: "'JetBrains Mono', monospace",
};

const GRID_STYLE = {
  stroke: 'rgba(255,255,255,0.06)',
  strokeDasharray: '2 4',
};

/* ── Custom Tooltip ───────────────────────────────────────────────────── */
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="trend-tooltip">
      <div className="trend-tooltip__header">{label}</div>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="trend-tooltip__row">
          <span
            className="trend-tooltip__dot"
            style={{ background: entry.color }}
          />
          <span className="trend-tooltip__label">{entry.name}</span>
          <span className="trend-tooltip__value">
            {typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Toggle Pill (CFR-chart style) ────────────────────────────────────── */
interface Toggle {
  key: string;
  label: string;
  color: string;
}

function ToggleGroup({
  toggles,
  visible,
  onToggle,
}: {
  toggles: Toggle[];
  visible: Set<string>;
  onToggle: (key: string) => void;
}) {
  return (
    <div className="trend-toggle-group">
      {toggles.map(t => (
        <button
          key={t.key}
          className={`trend-toggle ${visible.has(t.key) ? 'trend-toggle--active' : ''}`}
          onClick={() => onToggle(t.key)}
          style={
            visible.has(t.key)
              ? { '--toggle-color': t.color, '--toggle-glow': `${t.color}66` } as React.CSSProperties
              : undefined
          }
        >
          <span className="trend-toggle__indicator" style={visible.has(t.key) ? { background: t.color } : undefined} />
          <span className="trend-toggle__label">{t.label}</span>
        </button>
      ))}
    </div>
  );
}

/* ── 1. Solids vs Equipment Chart ─────────────────────────────────────── */
function SolidsVsEquipChart({ data, selectedDate }: { data: any[]; selectedDate: string | null }) {
  const [visible, setVisible] = useState(new Set(['solids', 'equip']));
  const toggle = (k: string) => setVisible(prev => {
    const next = new Set(prev);
    next.has(k) ? next.delete(k) : next.add(k);
    return next;
  });

  return (
    <div className="panel trend-chart animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Solids vs Equipment</h3>
        <ToggleGroup
          toggles={[
            { key: 'solids', label: 'Solids %', color: '#3b82f6' },
            { key: 'equip', label: 'Equip Hrs', color: '#10b981' },
          ]}
          visible={visible}
          onToggle={toggle}
        />
      </div>
      <div className="trend-chart__body">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="date" tick={AXIS_STYLE} tickLine={false} axisLine={false} />
            <YAxis yAxisId="left" tick={AXIS_STYLE} tickLine={false} axisLine={false} width={35} />
            <YAxis yAxisId="right" orientation="right" tick={AXIS_STYLE} tickLine={false} axisLine={false} width={35} />
            <Tooltip content={<ChartTooltip />} />
            {selectedDate && (
              <ReferenceLine x={selectedDate} stroke="rgba(0,212,255,0.3)" strokeDasharray="4 4" />
            )}
            {visible.has('solids') && (
              <Line yAxisId="left" type="monotone" dataKey="solids" name="Solids %" stroke="#3b82f6" strokeWidth={2} dot={false} animationDuration={800} />
            )}
            {visible.has('equip') && (
              <Line yAxisId="right" type="monotone" dataKey="totalEquipHours" name="Equip Hrs" stroke="#10b981" strokeWidth={2} dot={false} animationDuration={800} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ── 2. Rheology Chart ────────────────────────────────────────────────── */
function RheologyChart({ data, selectedDate }: { data: any[]; selectedDate: string | null }) {
  const [visible, setVisible] = useState(new Set(['pv', 'yp', 'gel10s']));
  const toggle = (k: string) => setVisible(prev => {
    const next = new Set(prev);
    next.has(k) ? next.delete(k) : next.add(k);
    return next;
  });

  return (
    <div className="panel trend-chart animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Rheology</h3>
        <ToggleGroup
          toggles={[
            { key: 'pv', label: 'PV', color: '#3b82f6' },
            { key: 'yp', label: 'YP', color: '#10b981' },
            { key: 'gel10s', label: 'Gel 10s', color: '#f59e0b' },
          ]}
          visible={visible}
          onToggle={toggle}
        />
      </div>
      <div className="trend-chart__body">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="date" tick={AXIS_STYLE} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={35} />
            <Tooltip content={<ChartTooltip />} />
            {selectedDate && (
              <ReferenceLine x={selectedDate} stroke="rgba(0,212,255,0.3)" strokeDasharray="4 4" />
            )}
            {visible.has('pv') && (
              <Line type="monotone" dataKey="pv" name="PV" stroke="#3b82f6" strokeWidth={2} dot={false} animationDuration={800} />
            )}
            {visible.has('yp') && (
              <Line type="monotone" dataKey="yp" name="YP" stroke="#10b981" strokeWidth={2} dot={false} animationDuration={800} />
            )}
            {visible.has('gel10s') && (
              <Line type="monotone" dataKey="gel10s" name="Gel 10s" stroke="#f59e0b" strokeWidth={2} dot={false} animationDuration={800} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ── 3. Chemical Usage Stacked Bar ────────────────────────────────────── */
const CATEGORY_COLORS: Record<string, string> = {
  'Base Fluid': '#3b82f6',
  'Weighting Agent': '#8b5cf6',
  'Viscosifier': '#10b981',
  'Thinner': '#f59e0b',
  'Fluid Loss Control': '#f43f5e',
  'pH Control': '#06b6d4',
  'LCM': '#ec4899',
  'Emulsifier': '#a78bfa',
  'SC Removal': '#ef4444',
  'Downhole Loss': '#78716c',
  'Recovered Mud': '#22d3ee',
  'Generic/Unknown': '#6b7280',
};

function ChemicalChart({ data, categories }: { data: any[]; categories: string[] }) {
  return (
    <div className="panel trend-chart animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Chemical Usage</h3>
      </div>
      <div className="trend-chart__body">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="date" tick={AXIS_STYLE} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={35} />
            <Tooltip content={<ChartTooltip />} />
            {categories.map(cat => (
              <Bar
                key={cat}
                dataKey={cat}
                name={cat}
                stackId="chem"
                fill={CATEGORY_COLORS[cat] || '#6b7280'}
                animationDuration={800}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ── 4. Mud Weight Area Chart ─────────────────────────────────────────── */
function MudWeightChart({ data, selectedDate }: { data: any[]; selectedDate: string | null }) {
  return (
    <div className="panel trend-chart animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Mud Weight</h3>
        <span className="trend-chart__unit">ppg</span>
      </div>
      <div className="trend-chart__body">
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <defs>
              <linearGradient id="mwGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="date" tick={AXIS_STYLE} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={35} domain={['dataMin - 0.5', 'dataMax + 0.5']} />
            <Tooltip content={<ChartTooltip />} />
            {selectedDate && (
              <ReferenceLine x={selectedDate} stroke="rgba(0,212,255,0.3)" strokeDasharray="4 4" />
            )}
            <Area
              type="monotone"
              dataKey="mw"
              name="Mud Weight"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="url(#mwGrad)"
              animationDuration={800}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Main TrendCharts Component
   ═══════════════════════════════════════════════════════════════════════════ */
export default function TrendCharts({ timeline, selectedDate }: Props) {
  // Build chart data from timeline (7-day window centered on selected date)
  const { lineData, chemData, categories } = useMemo(() => {
    if (!timeline.length || !selectedDate) {
      return { lineData: [], chemData: [], categories: [] };
    }

    const dateIdx = timeline.findIndex(d => d.date === selectedDate);
    const center = dateIdx >= 0 ? dateIdx : timeline.length - 1;
    const start = Math.max(0, center - 3);
    const end = Math.min(timeline.length, center + 4);
    const window = timeline.slice(start, end);

    // Line chart data
    const lineData = window.map(day => {
      const mp = day.mud_properties;
      // Sum all equipment hours
      const shakers = day.equipment?.shakers || [];
      const centrifuges = day.equipment?.centrifuges || [];
      const hydro = day.equipment?.hydrocyclones || {};
      const totalEquipHours =
        shakers.reduce((s, sh) => s + (sh.hours || 0), 0) +
        centrifuges.reduce((s, c) => s + (c.hours || 0), 0) +
        (hydro.desander?.hours || 0) +
        (hydro.desilter?.hours || 0) +
        (hydro.mud_cleaner?.hours || 0);

      return {
        date: day.date,
        solids: mp?.solids ?? null,
        pv: mp?.pv ?? null,
        yp: mp?.yp ?? null,
        gel10s: mp?.gel_10s ?? null,
        mw: mp?.mud_weight ?? null,
        totalEquipHours: Math.round(totalEquipHours * 10) / 10,
      };
    });

    // Chemical stacked bar data — aggregate by category per day
    const categorySet = new Set<string>();
    const chemData = window.map(day => {
      const row: Record<string, any> = { date: day.date };
      for (const chem of day.chemicals || []) {
        if (chem.add_loss?.toLowerCase() !== 'add') continue;
        const cat = chem.category || 'Generic/Unknown';
        categorySet.add(cat);
        row[cat] = (row[cat] || 0) + (chem.quantity || 0);
      }
      return row;
    });

    return {
      lineData,
      chemData,
      categories: Array.from(categorySet).sort(),
    };
  }, [timeline, selectedDate]);

  if (!timeline.length) {
    return (
      <div className="trend-charts trend-charts--empty">
        <p className="trend-charts__placeholder">Select a job to view trends</p>
      </div>
    );
  }

  return (
    <div className="trend-charts">
      <div className="trend-charts__grid">
        <SolidsVsEquipChart data={lineData} selectedDate={selectedDate} />
        <RheologyChart data={lineData} selectedDate={selectedDate} />
        <ChemicalChart data={chemData} categories={categories} />
        <MudWeightChart data={lineData} selectedDate={selectedDate} />
      </div>
    </div>
  );
}
