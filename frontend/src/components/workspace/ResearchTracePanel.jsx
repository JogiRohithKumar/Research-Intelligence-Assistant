import { useState, Fragment } from 'react';
import { Activity, ArrowDown, ChevronDown, ChevronUp, Terminal, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import EmptyState from './EmptyState';

export default function ResearchTracePanel({
  loopState,
  iterationsHistory = [],
  agentLogs = [],
  onEntityClick
}) {
  const [expandedIterIds, setExpandedIterIds] = useState(new Set([1]));
  const [showLogs, setShowLogs] = useState(false);

  // Normalize iterations list
  const iterations = (loopState?.iterations && loopState.iterations.length > 0)
    ? loopState.iterations
    : iterationsHistory;

  if (iterations.length === 0 && agentLogs.length === 0) {
    return (
      <EmptyState
        title="No Research Iterations Recorded"
        message="The Agentic Research Loop records iteration cycles, sufficiency evaluations, and query adaptation telemetry during execution."
        iconType="inbox"
      />
    );
  }

  const toggleIter = (id) => {
    setExpandedIterIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const getActionBadge = (action) => {
    if (action === 'CONTINUE_RESEARCH') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-950/60 border border-amber-800/60 text-amber-300">
          CONTINUE RESEARCH
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-950/60 border border-emerald-800/60 text-emerald-300">
        STOP RESEARCH
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* 1. Header with Stop Reason & Summary */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100">
            Agentic Research Loop Trace ({iterations.length} iterations)
          </h2>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {loopState?.final_stop_reason && (
            <span className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]">
              Final Stop: {loopState.final_stop_reason}
            </span>
          )}

          <button
            type="button"
            onClick={() => setShowLogs(!showLogs)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-colors"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>{showLogs ? 'Hide Agent Telemetry' : 'Show Agent Telemetry'}</span>
          </button>
        </div>
      </div>

      {/* 2. Step-by-Step Iteration Chain */}
      <div className="space-y-4">
        {iterations.map((iter, idx) => {
          const iterId = iter.iteration_id || idx + 1;
          const isExpanded = expandedIterIds.has(iterId);
          const decision = iter.decision || {};
          const isLast = idx === iterations.length - 1;

          return (
            <Fragment key={iterId}>
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-mono font-bold text-slate-300">
                      {iterId}
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">
                        Iteration {iterId}: "{iter.query_used}"
                      </h3>
                      {iter.timestamp && (
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(iter.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {getActionBadge(decision.action)}
                    <button
                      type="button"
                      onClick={() => toggleIter(iterId)}
                      className="p-1 rounded text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Iteration Empirical Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-500 block">New Papers</span>
                    <span className="font-semibold text-slate-200">+{iter.new_paper_count || 0} (cumul: {iter.cumulative_paper_count || 0})</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-500 block">New Evidence</span>
                    <span className="font-semibold text-slate-200">+{iter.new_evidence_count || 0} (cumul: {iter.cumulative_evidence_count || 0})</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-500 block">Supported Claims</span>
                    <span className="font-semibold text-emerald-400">{iter.supported_claims_count || 0}</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-500 block">Stop Reason</span>
                    <span className="font-mono text-slate-300 text-[11px] truncate block" title={iter.stop_reason || decision.stop_reason || 'N/A'}>
                      {iter.stop_reason || decision.stop_reason || '—'}
                    </span>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="pt-2 border-t border-slate-800/80 space-y-3 text-xs">
                    {/* Search Strategy / Rationale */}
                    {decision.rationale && (
                      <div className="bg-slate-950 p-3 rounded border border-slate-800">
                        <strong className="text-slate-300 block mb-1">Decision Rationale:</strong>
                        <p className="text-slate-400 leading-relaxed">{decision.rationale}</p>
                      </div>
                    )}

                    {/* Targeted Gap */}
                    {decision.selected_gap && (
                      <div className="bg-indigo-950/20 border border-indigo-900/40 p-3 rounded space-y-1">
                        <span className="text-[10px] font-mono font-semibold uppercase text-indigo-300">
                          Targeted Gap Addressed:
                        </span>
                        <p className="text-slate-300 leading-relaxed">
                          {decision.selected_gap.description || decision.selected_gap.gap_id}
                        </p>
                      </div>
                    )}

                    {/* Retrieved Papers IDs */}
                    {iter.retrieved_paper_ids && iter.retrieved_paper_ids.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[10px] font-mono text-slate-500">Papers in Cycle:</span>
                        {iter.retrieved_paper_ids.map((pid) => (
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

                    {/* Retrieved Evidence IDs */}
                    {iter.retrieved_evidence_ids && iter.retrieved_evidence_ids.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[10px] font-mono text-slate-500">Evidence Chunks:</span>
                        {iter.retrieved_evidence_ids.map((eid) => (
                          <button
                            key={eid}
                            type="button"
                            onClick={() => onEntityClick && onEntityClick('evidence', eid)}
                            className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-950 text-sky-300 border border-sky-800 hover:bg-sky-900 transition-colors"
                          >
                            {eid}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {!isLast && (
                <div className="flex justify-center py-1">
                  <div className="w-8 h-8 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
                    <ArrowDown className="w-4 h-4" />
                  </div>
                </div>
              )}
            </Fragment>
          );
        })}
      </div>

      {/* 3. Real Backend Agent Logs Telemetry Stream */}
      {showLogs && agentLogs.length > 0 && (
        <section className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Authoritative Agent Execution Telemetry ({agentLogs.length} events)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500">Live Backend Trace</span>
          </div>

          <div className="bg-slate-950 p-3 rounded border border-slate-800 space-y-2 max-h-80 overflow-y-auto font-mono text-xs">
            {agentLogs.map((log, li) => {
              const status = log.status || 'info';
              return (
                <div key={li} className="flex items-start gap-2.5 py-1 border-b border-slate-900 last:border-0">
                  {status === 'success' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  ) : status === 'warning' ? (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  ) : status === 'failed' ? (
                    <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                  ) : (
                    <Activity className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-0.5 flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-bold uppercase text-indigo-400">
                        [{log.agent || 'GRAPH'}]
                      </span>
                      {log.timestamp && (
                        <span className="text-[10px] text-slate-600">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed break-words">
                      {log.message || log.error || 'Agent executed successfully.'}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
