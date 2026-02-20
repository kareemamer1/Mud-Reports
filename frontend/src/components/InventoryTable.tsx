/* ═══════════════════════════════════════════════════════════════════════════
   InventoryTable — sortable chemical inventory with category badges
   ═══════════════════════════════════════════════════════════════════════════ */
import { useState, useMemo } from 'react';
import type { ChemicalEntry } from '../services/insightsApi';
import './InventoryTable.css';

interface Props {
  chemicals: ChemicalEntry[];
}

type SortKey = 'item' | 'add_loss' | 'quantity' | 'category';
type SortDir = 'asc' | 'desc';

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

export default function InventoryTable({ chemicals }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('category');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const sorted = useMemo(() => {
    const arr = [...chemicals];
    arr.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'item': cmp = a.item.localeCompare(b.item); break;
        case 'add_loss': cmp = a.add_loss.localeCompare(b.add_loss); break;
        case 'quantity': cmp = (a.quantity || 0) - (b.quantity || 0); break;
        case 'category': cmp = (a.category || '').localeCompare(b.category || ''); break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [chemicals, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  function SortIndicator({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="inv-sort inv-sort--inactive">⇅</span>;
    return <span className="inv-sort">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  }

  return (
    <div className="panel inv-table animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Inventory</h3>
        <span className="inv-table__count">{chemicals.length} items</span>
      </div>
      <div className="inv-table__scroll">
        <table className="inv-table__table">
          <thead>
            <tr>
              <th onClick={() => toggleSort('item')}>
                Item <SortIndicator col="item" />
              </th>
              <th onClick={() => toggleSort('add_loss')}>
                Add/Loss <SortIndicator col="add_loss" />
              </th>
              <th onClick={() => toggleSort('quantity')}>
                Qty <SortIndicator col="quantity" />
              </th>
              <th>Units</th>
              <th onClick={() => toggleSort('category')}>
                Category <SortIndicator col="category" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={5} className="inv-table__empty">No chemical data</td>
              </tr>
            ) : (
              sorted.map((c, i) => (
                <tr key={i}>
                  <td className="inv-table__item">{c.item}</td>
                  <td>
                    <span className={`inv-table__addloss inv-table__addloss--${c.add_loss.toLowerCase()}`}>
                      {c.add_loss}
                    </span>
                  </td>
                  <td className="inv-table__qty">{c.quantity?.toFixed(1)}</td>
                  <td className="inv-table__units">{c.units}</td>
                  <td>
                    <span
                      className="inv-table__category"
                      style={{
                        borderColor: CATEGORY_COLORS[c.category] || '#6b7280',
                        color: CATEGORY_COLORS[c.category] || '#6b7280',
                      }}
                    >
                      {c.category}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
