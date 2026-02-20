/* ═══════════════════════════════════════════════════════════════════════════
   MudPropsSnapshot — grid display of mud properties with delta arrows
   ═══════════════════════════════════════════════════════════════════════════ */
import type { MudProperties } from '../services/insightsApi';
import './MudPropsSnapshot.css';

interface Props {
  current: MudProperties | null;
  previous: MudProperties | null;
}

interface PropDef {
  key: keyof MudProperties;
  label: string;
  unit: string;
  decimals: number;
}

const PROP_DEFS: PropDef[] = [
  { key: 'mud_weight', label: 'MW', unit: 'ppg', decimals: 1 },
  { key: 'pv', label: 'PV', unit: 'cP', decimals: 0 },
  { key: 'yp', label: 'YP', unit: 'lb/100ft²', decimals: 0 },
  { key: 'gel_10s', label: 'Gel 10s', unit: 'lb/100ft²', decimals: 0 },
  { key: 'solids', label: 'Solids', unit: '%', decimals: 1 },
  { key: 'sand', label: 'Sand', unit: '%', decimals: 2 },
  { key: 'lgs', label: 'LGS', unit: '%', decimals: 1 },
  { key: 'drill_solids', label: 'Drill Sol', unit: '%', decimals: 1 },
  { key: 'ph', label: 'pH', unit: '', decimals: 1 },
];

function DeltaArrow({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) {
    return <span className="mud-delta mud-delta--neutral">—</span>;
  }
  if (delta > 0) {
    return <span className="mud-delta mud-delta--up">▲ {Math.abs(delta).toFixed(1)}</span>;
  }
  return <span className="mud-delta mud-delta--down">▼ {Math.abs(delta).toFixed(1)}</span>;
}

export default function MudPropsSnapshot({ current, previous }: Props) {
  if (!current) {
    return (
      <div className="panel mud-snap mud-snap--empty">
        <div className="panel__header">
          <h3 className="panel__title">Mud Properties</h3>
        </div>
        <div className="panel__body">
          <p className="mud-snap__placeholder">No mud data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="panel mud-snap animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Mud Properties</h3>
        <span className="mud-snap__samples">
          {current.samples_count} sample{current.samples_count !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="panel__body">
        <div className="mud-snap__grid stagger-children">
          {PROP_DEFS.map(def => {
            const val = current[def.key] as number | null;
            const prevVal = previous ? (previous[def.key] as number | null) : null;
            const delta =
              val !== null && prevVal !== null ? val - prevVal : null;

            return (
              <div key={def.key} className="mud-snap__card">
                <span className="mud-snap__label">{def.label}</span>
                <span className="mud-snap__value">
                  {val !== null ? val.toFixed(def.decimals) : '—'}
                </span>
                {def.unit && <span className="mud-snap__unit">{def.unit}</span>}
                <DeltaArrow delta={delta} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
