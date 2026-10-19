import { HelpCircle, Lightbulb } from 'lucide-react';
import EmptyState from './EmptyState';

export default function ResearchGapPanel({
  gaps = [],
  actionableGaps = [],
  onEntityClick
}) {
  // Combine Stage 4 research_gaps and Stage 5 actionable_gaps if both exist
  const allGaps = gaps.length > 0 ? gaps : actionableGaps;

  if (allGaps.length === 0) {
    return (
      <EmptyState
        title="No Research Gaps Identified"
        message="No empirical research gaps were identified within the retrieved literature corpus for this query."
        iconType="shield"
      />
    );
  }

  const getSeverityBadge = (sev) => {
    const s = (sev || 'MEDIUM').toUpperCase();
    if (s === 'HIGH') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/70 border border-rose-800 text-rose-300">
          SEVERITY: HIGH
        </span>
      );
    }
    if (s === 'LOW') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 border border-slate-700 text-slate-300">
          SEVERITY: LOW
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-950/60 border border-amber-800/60 text-amber-300">
        SEVERITY: MEDIUM
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-100">
            Identified Research Gaps ({allGaps.length})
          </h2>
        </div>
        <p className="text-[11px] font-mono text-slate-400">
          * Strictly qualified: Within the retrieved literature corpus
        </p>
      </div>

      <div className="space-y-4">
        {allGaps.map((gap, idx) => {
          const gapId = gap.gap_id || `G00${idx + 1}`;
          const category = gap.category || 'EVIDENCE_GAP';
          const description = gap.description || (typeof gap === 'string' ? gap : 'No description provided');
          const reasoning = gap.reasoning || '';
          const affectedPapers = gap.affected_papers || [];
          const evidenceIds = gap.supporting_evidence_ids || gap.evidence_ids || [];
          const recommendedAction = gap.recommended_research_action || '';

          return (
            <div key={gapId || idx} className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 pb-2 border-b border-slate-800">
                <div className="space-y-0.5">
                  <span className="text-[10px] font-mono text-slate-500 uppercase">{gapId}</span>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-950/50 border border-amber-800/50 text-amber-300 uppercase">
                      {category.replace(/_/g, ' ')}
                    </span>
                    {getSeverityBadge(gap.severity || gap.impact)}
                  </div>
                </div>
              </div>

              {/* Description */}
              <div className="bg-slate-950 p-3.5 rounded border border-slate-800">
                <p className="text-xs text-slate-200 leading-relaxed font-sans">
                  {description}
                </p>
              </div>

              {/* Reasoning */}
              {reasoning && (
                <div className="text-xs text-slate-400 leading-relaxed">
                  <strong className="text-slate-300">Empirical Justification: </strong>
                  {reasoning}
                </div>
              )}

              {/* Recommended Action */}
              {recommendedAction && (
                <div className="flex items-start gap-2 bg-indigo-950/20 border border-indigo-900/40 p-2.5 rounded text-xs text-indigo-300">
                  <Lightbulb className="w-3.5 h-3.5 mt-0.5 shrink-0 text-indigo-400" />
                  <div>
                    <span className="font-semibold text-indigo-200">Recommended Follow-up Research: </span>
                    <span>{recommendedAction}</span>
                  </div>
                </div>
              )}

              {/* Provenance: Affected Papers & Evidence */}
              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60 text-xs">
                {affectedPapers.length > 0 && (
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] font-mono text-slate-400">Affected Papers:</span>
                    {affectedPapers.map((pid) => (
                      <button
                        key={pid}
                        type="button"
                        onClick={() => onEntityClick && onEntityClick('paper', pid)}
                        className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-colors truncate max-w-[120px]"
                      >
                        {pid}
                      </button>
                    ))}
                  </div>
                )}

                {evidenceIds.length > 0 && (
                  <div className="flex items-center gap-1 ml-auto">
                    <span className="text-[10px] font-mono text-slate-400">Evidence:</span>
                    {evidenceIds.map((eid) => (
                      <button
                        key={eid}
                        type="button"
                        onClick={() => onEntityClick && onEntityClick('evidence', eid)}
                        className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-950/80 text-sky-300 border border-sky-800 hover:bg-sky-900 transition-colors"
                      >
                        {eid}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
