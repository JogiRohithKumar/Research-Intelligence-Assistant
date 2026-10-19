import { GitFork, AlertTriangle, Info } from 'lucide-react';
import EmptyState from './EmptyState';

export default function ContradictionPanel({
  contradictions = [],
  onEntityClick
}) {
  if (contradictions.length === 0) {
    return (
      <EmptyState
        title="No Contradictions Detected"
        message="No verified contradictions were detected in the retrieved literature."
        iconType="shield"
      />
    );
  }

  const getContradictionBadge = (type, isGenuine) => {
    if (isGenuine) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-rose-950/70 border border-rose-800 text-rose-300">
          <AlertTriangle className="w-3 h-3 text-rose-400" />
          GENUINE CONTRADICTION
        </span>
      );
    }

    const typeStr = (type || 'DISCREPANCY').toUpperCase();
    const map = {
      METHODOLOGY_DEPENDENT: { label: 'METHODOLOGY DIFFERENCE', color: 'bg-amber-950/60 border-amber-800/60 text-amber-300' },
      POPULATION_CONFLICT: { label: 'POPULATION DIFFERENCE', color: 'bg-amber-950/60 border-amber-800/60 text-amber-300' },
      OUTCOME_DEFINITION_DIFFERENCE: { label: 'OUTCOME DEFINITION DIFFERENCE', color: 'bg-sky-950/60 border-sky-800/60 text-sky-300' },
      CONTEXT_DEPENDENT: { label: 'CONTEXT DEPENDENT', color: 'bg-indigo-950/60 border-indigo-800/60 text-indigo-300' },
      DIRECTIONAL_CONFLICT: { label: 'DIRECTIONAL CONFLICT', color: 'bg-orange-950/60 border-orange-800/60 text-orange-300' },
      DIRECT_RESULT_CONFLICT: { label: 'RESULT CONFLICT', color: 'bg-rose-950/60 border-rose-800/60 text-rose-300' },
    };

    const style = map[typeStr] || { label: typeStr.replace(/_/g, ' '), color: 'bg-slate-800 border-slate-700 text-slate-300' };

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium border ${style.color}`}>
        <Info className="w-3 h-3" />
        {style.label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitFork className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-100">
            Empirical Contradictions & Methodological Discrepancies ({contradictions.length})
          </h2>
        </div>
        <p className="text-xs text-slate-400 hidden sm:block">
          Distingushes substantive conflicts from differences in methodology, population, and dataset
        </p>
      </div>

      <div className="space-y-4">
        {contradictions.map((ct, idx) => (
          <div key={idx} className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-4">
            {/* Header: Topic & Classification Badge */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
              <div className="space-y-0.5">
                <span className="text-[10px] font-mono text-slate-500 uppercase">{ct.contradiction_id || `CT00${idx + 1}`}</span>
                <h3 className="text-sm font-semibold text-slate-100">{ct.topic || "Empirical Discrepancy"}</h3>
              </div>
              <div className="shrink-0">
                {getContradictionBadge(ct.contradiction_type, ct.is_genuine_contradiction)}
              </div>
            </div>

            {/* Claims Comparison Matrix (Paper A vs Paper B) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-950 p-3.5 rounded border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-semibold uppercase text-indigo-400">Study A</span>
                  <button
                    type="button"
                    onClick={() => onEntityClick && onEntityClick('paper', ct.paper_a_id)}
                    className="text-[10px] font-mono text-slate-400 hover:text-indigo-300 underline underline-offset-2"
                  >
                    ID: {ct.paper_a_id}
                  </button>
                </div>
                <p className="text-slate-200 leading-relaxed font-sans">{ct.claim_a}</p>
              </div>

              <div className="bg-slate-950 p-3.5 rounded border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-semibold uppercase text-amber-400">Study B</span>
                  <button
                    type="button"
                    onClick={() => onEntityClick && onEntityClick('paper', ct.paper_b_id)}
                    className="text-[10px] font-mono text-slate-400 hover:text-amber-300 underline underline-offset-2"
                  >
                    ID: {ct.paper_b_id}
                  </button>
                </div>
                <p className="text-slate-200 leading-relaxed font-sans">{ct.claim_b}</p>
              </div>
            </div>

            {/* Possible Explanations / Methodological Grounding */}
            {ct.possible_explanations && ct.possible_explanations.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] font-mono uppercase text-slate-400">Grounded Explanations / Differences:</span>
                <ul className="space-y-1 pl-4 list-disc text-xs text-slate-300 leading-relaxed">
                  {ct.possible_explanations.map((exp, ei) => (
                    <li key={ei}>{exp}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Evidence References */}
            {ct.evidence_ids && ct.evidence_ids.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-800/60 text-xs">
                <span className="text-[10px] font-mono text-slate-400">Supporting Evidence Chunks:</span>
                {ct.evidence_ids.map((eid) => (
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
        ))}
      </div>
    </div>
  );
}
