/* ═══════════════════════════════════════════════════════════════════════════
   DateSlider — date navigation with keyboard support
   ═══════════════════════════════════════════════════════════════════════════ */
import { useState, useCallback, useMemo } from 'react';
import { format, parseISO, differenceInDays } from 'date-fns';
import './DateSlider.css';

interface Props {
  dates: string[];          // ISO date strings, sorted ascending
  selectedDate: string | null;
  onDateChange: (date: string) => void;
}

export default function DateSlider({ dates, selectedDate, onDateChange }: Props) {
  const idx = selectedDate ? dates.indexOf(selectedDate) : -1;
  const total = dates.length;

  // Track a "preview" index while the user is dragging, null when idle
  const [draggingIdx, setDraggingIdx] = useState<number | null>(null);

  const displayIdx = draggingIdx ?? idx;
  const displayDate = displayIdx >= 0 ? dates[displayIdx] : null;

  const dateObj = useMemo(
    () => (displayDate ? parseISO(displayDate) : null),
    [displayDate],
  );

  const dayRange = useMemo(() => {
    if (dates.length < 2) return 0;
    return differenceInDays(parseISO(dates[dates.length - 1]), parseISO(dates[0]));
  }, [dates]);

  const goPrev = useCallback(() => {
    if (idx > 0) onDateChange(dates[idx - 1]);
  }, [idx, dates, onDateChange]);

  const goNext = useCallback(() => {
    if (idx < total - 1) onDateChange(dates[idx + 1]);
  }, [idx, total, dates, onDateChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); goPrev(); }
      if (e.key === 'ArrowRight') { e.preventDefault(); goNext(); }
    },
    [goPrev, goNext],
  );

  if (dates.length === 0) {
    return (
      <div className="date-slider date-slider--empty">
        <span className="date-slider__placeholder">No dates available</span>
      </div>
    );
  }

  return (
    <div className="date-slider" onKeyDown={handleKeyDown} tabIndex={0}>
      <button
        className="date-slider__btn"
        onClick={goPrev}
        disabled={idx <= 0}
        aria-label="Previous day"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M8.5 3.5L5 7L8.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      <div className="date-slider__center">
        <div className="date-slider__date-display">
          {dateObj && (
            <>
              <span className="date-slider__weekday">{format(dateObj, 'EEE')}</span>
              <span className="date-slider__date">{format(dateObj, 'MMM d, yyyy')}</span>
            </>
          )}
        </div>

        <input
          type="range"
          className="date-slider__range"
          min={0}
          max={total - 1}
          value={displayIdx >= 0 ? displayIdx : 0}
          onChange={e => setDraggingIdx(Number(e.target.value))}
          onMouseUp={e => {
            const val = Number((e.target as HTMLInputElement).value);
            setDraggingIdx(null);
            onDateChange(dates[val]);
          }}
          onTouchEnd={e => {
            const val = Number((e.target as HTMLInputElement).value);
            setDraggingIdx(null);
            onDateChange(dates[val]);
          }}
          aria-label="Date slider"
        />

        <div className="date-slider__info">
          <span className="date-slider__counter">
            Day {displayIdx + 1} of {total}
          </span>
          {dayRange > 0 && (
            <span className="date-slider__range-label">
              {dayRange} day span
            </span>
          )}
        </div>
      </div>

      <button
        className="date-slider__btn"
        onClick={goNext}
        disabled={idx >= total - 1}
        aria-label="Next day"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M5.5 3.5L9 7L5.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  );
}
