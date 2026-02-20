/* ═══════════════════════════════════════════════════════════════════════════
   EquipmentStatus — horizontal bar visualization of equipment hours
   ═══════════════════════════════════════════════════════════════════════════ */
import type { EquipmentData } from '../services/insightsApi';
import './EquipmentStatus.css';

interface Props {
  equipment: EquipmentData | null;
}

function statusColor(hours: number): string {
  if (hours >= 18) return 'var(--color-severity-low)';
  if (hours >= 6) return 'var(--color-severity-medium)';
  return 'var(--color-severity-high)';
}

function statusClass(hours: number): string {
  if (hours >= 18) return 'good';
  if (hours >= 6) return 'warn';
  return 'down';
}

function BarRow({ label, hours, sub }: { label: string; hours: number | null; sub?: string }) {
  const h = hours ?? 0;
  const pct = Math.min((h / 24) * 100, 100);
  const cls = statusClass(h);

  return (
    <div className="equip__row">
      <div className="equip__label-col">
        <span className="equip__name">{label}</span>
        {sub && <span className="equip__sub">{sub}</span>}
      </div>
      <div className="equip__bar-col">
        <div className="equip__bar-track">
          <div
            className={`equip__bar-fill equip__bar-fill--${cls}`}
            style={{ width: `${pct}%`, backgroundColor: statusColor(h) }}
          />
        </div>
      </div>
      <span className={`equip__hours equip__hours--${cls}`}>
        {(hours ?? 0).toFixed(1)}h
      </span>
    </div>
  );
}

export default function EquipmentStatus({ equipment }: Props) {
  if (!equipment) {
    return (
      <div className="panel equip equip--empty">
        <div className="panel__header">
          <h3 className="panel__title">Equipment Status</h3>
        </div>
        <div className="panel__body">
          <p className="equip__placeholder">No equipment data</p>
        </div>
      </div>
    );
  }

  const { shakers, centrifuges, hydrocyclones } = equipment;

  return (
    <div className="panel equip animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Equipment Status</h3>
        <span className="equip__scale-label">0 ─── 24h</span>
      </div>
      <div className="panel__body stagger-children">
        {/* Shakers */}
        {shakers.map((s, i) => (
          <BarRow
            key={`shaker-${i}-${s.name}`}
            label={s.name}
            hours={s.hours}
            sub={s.mesh.filter(Boolean).length > 0
              ? `Mesh: ${s.mesh.filter(Boolean).join('/')}`
              : undefined
            }
          />
        ))}

        {/* Centrifuges */}
        {centrifuges.map((c, i) => (
          <BarRow
            key={`cent-${i}-${c.name}`}
            label={c.name}
            hours={c.hours}
            sub={[c.type, c.feed_rate ? `${c.feed_rate} gpm` : null]
              .filter(Boolean)
              .join(' • ')}
          />
        ))}

        {/* Hydrocyclones */}
        {hydrocyclones.desander && (
          <BarRow
            label="Desander"
            hours={hydrocyclones.desander.hours}
            sub={[hydrocyclones.desander.size, hydrocyclones.desander.cones ? `${hydrocyclones.desander.cones} cones` : null]
              .filter(Boolean)
              .join(' • ')}
          />
        )}
        {hydrocyclones.desilter && (
          <BarRow
            label="Desilter"
            hours={hydrocyclones.desilter.hours}
            sub={[hydrocyclones.desilter.size, hydrocyclones.desilter.cones ? `${hydrocyclones.desilter.cones} cones` : null]
              .filter(Boolean)
              .join(' • ')}
          />
        )}
        {hydrocyclones.mud_cleaner && (hydrocyclones.mud_cleaner.hours ?? 0) > 0 && (
          <BarRow
            label="Mud Cleaner"
            hours={hydrocyclones.mud_cleaner.hours}
          />
        )}
      </div>
    </div>
  );
}
