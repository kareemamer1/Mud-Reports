/* ═══════════════════════════════════════════════════════════════════════════
   JobSelector — searchable dropdown for job selection
   ═══════════════════════════════════════════════════════════════════════════ */
import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import type { Job } from '../services/insightsApi';
import './JobSelector.css';

const MAX_VISIBLE = 50;

interface Props {
  jobs: Job[];
  selectedJobId: string | null;
  onSelect: (jobId: string) => void;
  loading?: boolean;
}

export default function JobSelector({ jobs, selectedJobId, onSelect, loading }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [focusIdx, setFocusIdx] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const filtered = useMemo(
    () => jobs.filter(j => j.job_id.toLowerCase().includes(search.toLowerCase())),
    [jobs, search],
  );

  const visible = useMemo(
    () => filtered.slice(0, MAX_VISIBLE),
    [filtered],
  );

  const selectedJob = jobs.find(j => j.job_id === selectedJobId);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Scroll focused item into view
  useEffect(() => {
    if (focusIdx >= 0 && listRef.current) {
      const el = listRef.current.children[focusIdx] as HTMLElement;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [focusIdx]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!open) {
        if (e.key === 'Enter' || e.key === 'ArrowDown') {
          setOpen(true);
          e.preventDefault();
        }
        return;
      }
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setFocusIdx(i => Math.min(i + 1, visible.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusIdx(i => Math.max(i - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (focusIdx >= 0 && visible[focusIdx]) {
            onSelect(visible[focusIdx].job_id);
            setOpen(false);
            setSearch('');
          }
          break;
        case 'Escape':
          setOpen(false);
          setSearch('');
          break;
      }
    },
    [open, visible, focusIdx, onSelect],
  );

  return (
    <div className="job-selector" ref={containerRef} onKeyDown={handleKeyDown}>
      <button
        className={`job-selector__trigger ${open ? 'job-selector__trigger--open' : ''}`}
        onClick={() => {
          setOpen(!open);
          setSearch('');
          setFocusIdx(-1);
        }}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {loading ? (
          <span className="job-selector__loading">Loading jobs…</span>
        ) : selectedJob ? (
          <>
            <span className="job-selector__job-id">{selectedJob.job_id}</span>
            <span className="job-selector__meta">
              {selectedJob.first_date} → {selectedJob.last_date}
            </span>
          </>
        ) : (
          <span className="job-selector__placeholder">Select a job…</span>
        )}
        <svg className="job-selector__chevron" width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="job-selector__dropdown">
          <div className="job-selector__search-wrap">
            <input
              className="job-selector__search"
              type="text"
              placeholder="Search jobs…"
              value={search}
              onChange={e => {
                setSearch(e.target.value);
                setFocusIdx(0);
              }}
              autoFocus
            />
          </div>
          <ul className="job-selector__list" ref={listRef} role="listbox">
            {visible.length === 0 ? (
              <li className="job-selector__empty">No matching jobs</li>
            ) : (
              visible.map((job, idx) => (
                <li
                  key={job.job_id}
                  className={`job-selector__item ${
                    job.job_id === selectedJobId ? 'job-selector__item--selected' : ''
                  } ${idx === focusIdx ? 'job-selector__item--focused' : ''}`}
                  role="option"
                  aria-selected={job.job_id === selectedJobId}
                  onClick={() => {
                    onSelect(job.job_id);
                    setOpen(false);
                    setSearch('');
                  }}
                  onMouseEnter={() => setFocusIdx(idx)}
                >
                  <span className="job-selector__item-id">{job.job_id}</span>
                  <span className="job-selector__item-info">
                    {job.report_count} days &middot; {job.sample_count} samples
                  </span>
                  <span className="job-selector__item-dates">
                    {job.first_date} → {job.last_date}
                  </span>
                </li>
              ))
            )}
            {filtered.length > MAX_VISIBLE && (
              <li className="job-selector__hint">
                Showing {MAX_VISIBLE} of {filtered.length} — type to narrow
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
