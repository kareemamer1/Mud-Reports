/* ═══════════════════════════════════════════════════════════════════════════
   Dashboard — main page assembling all components
   ═══════════════════════════════════════════════════════════════════════════ */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import JobSelector from '../components/JobSelector';
import DateSlider from '../components/DateSlider';
import EquipmentStatus from '../components/EquipmentStatus';
import MudPropsSnapshot from '../components/MudPropsSnapshot';
import TrendCharts from '../components/TrendCharts';
import EventCards from '../components/EventCards';
import InventoryTable from '../components/InventoryTable';
import ReportRemarks from '../components/ReportRemarks';
import AgentPlaceholder from '../components/AgentPlaceholder';
import {
  getJobs,
  getTimeline,
  getInsights,
  getReportPdfUrl,
  type Job,
  type TimelineDay,
  type InsightsResponse,
} from '../services/insightsApi';
import './Dashboard.css';

export default function Dashboard() {
  const { jobId: paramJobId, date: paramDate } = useParams();
  const navigate = useNavigate();

  /* ── State ────────────────────────────────────────────────────────────── */
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(paramJobId || null);
  const [timeline, setTimeline] = useState<TimelineDay[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(paramDate || null);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);

  const dates = useMemo(() => timeline.map(d => d.date), [timeline]);

  // Current and previous day data
  const currentDay = useMemo(
    () => timeline.find(d => d.date === selectedDate) || null,
    [timeline, selectedDate],
  );
  const previousDay = useMemo(() => {
    if (!selectedDate || !timeline.length) return null;
    const idx = timeline.findIndex(d => d.date === selectedDate);
    return idx > 0 ? timeline[idx - 1] : null;
  }, [timeline, selectedDate]);

  /* ── Data Fetching ────────────────────────────────────────────────────── */
  // Load jobs on mount
  useEffect(() => {
    (async () => {
      try {
        const data = await getJobs();
        setJobs(data);
      } catch (err) {
        console.error('Failed to load jobs:', err);
      } finally {
        setJobsLoading(false);
      }
    })();
  }, []);

  // Load timeline when job changes
  useEffect(() => {
    if (!selectedJobId) return;
    setTimelineLoading(true);
    (async () => {
      try {
        const data = await getTimeline(selectedJobId);
        setTimeline(data);
        // Auto-select first date if none selected or current date not in range
        if (data.length > 0) {
          if (!selectedDate || !data.find(d => d.date === selectedDate)) {
            setSelectedDate(data[0].date);
          }
        }
      } catch (err) {
        console.error('Failed to load timeline:', err);
        setTimeline([]);
      } finally {
        setTimelineLoading(false);
      }
    })();
  }, [selectedJobId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load insights when date changes (cancel stale requests)
  useEffect(() => {
    if (!selectedJobId || !selectedDate) {
      setInsights(null);
      return;
    }
    const controller = new AbortController();
    (async () => {
      try {
        const data = await getInsights(selectedJobId, selectedDate, controller.signal);
        if (!controller.signal.aborted) setInsights(data);
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Failed to load insights:', err);
          setInsights(null);
        }
      }
    })();
    return () => controller.abort();
  }, [selectedJobId, selectedDate]);

  /* ── Handlers ─────────────────────────────────────────────────────────── */
  const handleJobSelect = useCallback(
    (jobId: string) => {
      setSelectedJobId(jobId);
      setSelectedDate(null);
      setTimeline([]);
      setInsights(null);
      navigate(`/dashboard/${jobId}`, { replace: true });
    },
    [navigate],
  );

  const handleDateChange = useCallback(
    (date: string) => {
      setSelectedDate(date);
      if (selectedJobId) {
        navigate(`/dashboard/${selectedJobId}/${date}`, { replace: true });
      }
    },
    [selectedJobId, navigate],
  );

  const handlePdfDownload = useCallback(() => {
    if (selectedJobId && selectedDate) {
      window.open(getReportPdfUrl(selectedJobId, selectedDate, 'day'), '_blank');
    }
  }, [selectedJobId, selectedDate]);

  /* ── Render ───────────────────────────────────────────────────────────── */
  return (
    <div className="dashboard">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="dashboard__header">
        <div className="dashboard__header-left">
          <h1 className="dashboard__logo">
            <span className="dashboard__logo-icon">◆</span>
            Solids Control
          </h1>
          <JobSelector
            jobs={jobs}
            selectedJobId={selectedJobId}
            onSelect={handleJobSelect}
            loading={jobsLoading}
          />
        </div>
        <div className="dashboard__header-center">
          <DateSlider
            dates={dates}
            selectedDate={selectedDate}
            onDateChange={handleDateChange}
          />
        </div>
        <div className="dashboard__header-right">
          {currentDay && (
            <div className="dashboard__depth">
              <span className="dashboard__depth-label">MD</span>
              <span className="dashboard__depth-value">
                {currentDay.depth_md?.toFixed(0) || '—'}
              </span>
              <span className="dashboard__depth-unit">ft</span>
            </div>
          )}
          <button
            className="dashboard__pdf-btn"
            onClick={handlePdfDownload}
            disabled={!selectedJobId || !selectedDate}
            title="Download PDF Report"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 12H12M8 2V9M8 9L5 6M8 9L11 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            PDF
          </button>
        </div>
      </header>

      {/* ── Loading State ───────────────────────────────────────────────── */}
      {timelineLoading && (
        <div className="dashboard__loading">
          <div className="dashboard__loading-bar" />
        </div>
      )}

      {/* ── Empty State ─────────────────────────────────────────────────── */}
      {!selectedJobId && !jobsLoading && (
        <div className="dashboard__empty">
          <div className="dashboard__empty-content">
            <span className="dashboard__empty-icon">◆</span>
            <h2 className="dashboard__empty-title">Solids Control Insight System</h2>
            <p className="dashboard__empty-desc">Select a job from the dropdown above to begin analysis.</p>
          </div>
        </div>
      )}

      {/* ── Main Content ────────────────────────────────────────────────── */}
      {selectedJobId && currentDay && (
        <main className="dashboard__content stagger-children">
          {/* Row 1: Equipment + Mud Props side by side */}
          <div className="dashboard__row-split">
            <EquipmentStatus equipment={currentDay.equipment} />
            <MudPropsSnapshot
              current={currentDay.mud_properties}
              previous={previousDay?.mud_properties || null}
            />
          </div>

          {/* Row 2: Trend Charts (2×2 grid) */}
          <TrendCharts timeline={timeline} selectedDate={selectedDate} />

          {/* Row 3: Events */}
          <EventCards
            insights={insights?.insights || []}
            summary={insights?.summary || ''}
            timeline={timeline}
            selectedDate={selectedDate}
          />

          {/* Row 4: Inventory */}
          <InventoryTable chemicals={currentDay.chemicals || []} />

          {/* Row 5: Remarks */}
          <ReportRemarks
            remarks={currentDay.remarks}
            engineer={currentDay.engineer}
            activity={currentDay.activity}
          />

          {/* Row 6: Agent */}
          <AgentPlaceholder />
        </main>
      )}
    </div>
  );
}
