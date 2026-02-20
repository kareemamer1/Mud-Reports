/* ═══════════════════════════════════════════════════════════════════════════
   ReportRemarks — raw remarks text display
   ═══════════════════════════════════════════════════════════════════════════ */
import './ReportRemarks.css';

interface Props {
  remarks: string | null;
  engineer: string | null;
  activity: string | null;
}

export default function ReportRemarks({ remarks, engineer, activity }: Props) {
  return (
    <div className="panel remarks animate-in">
      <div className="panel__header">
        <h3 className="panel__title">Report Remarks</h3>
        {engineer && <span className="remarks__engineer">{engineer}</span>}
      </div>
      <div className="panel__body">
        {activity && (
          <div className="remarks__activity">
            <span className="remarks__activity-label">Activity</span>
            <span className="remarks__activity-text">{activity}</span>
          </div>
        )}
        <pre className="remarks__text">
          {remarks || 'No remarks recorded for this date.'}
        </pre>
      </div>
    </div>
  );
}
