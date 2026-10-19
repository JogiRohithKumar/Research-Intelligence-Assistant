import { useState } from 'react';
import { CheckCircle2, AlertCircle, HelpCircle, Layers, Filter } from 'lucide-react';
import EmptyState from './EmptyState';

export default function FindingsClaimsPanel({
  findings = [],
  claims = [],
  onEntityClick
}) {
  const [filterMode, setFilterMode] = useState('all'); // 'all', 'findings', 'claims'
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'SUPPORTED', 'PARTIALLY_SUPPORTED', 'UNSUPPORTED'

  const hasItems = findings.length > 0 || claims.length > 0;

  if (!hasItems) {
    return (
      <EmptyState
        title="No Findings or Claims Extracted"
        message="Findings and atomic claims are derived through semantic evidence grounding during graph execution."
        iconType="inbox"
      />
    );
  }

  // Filter logic
  const filteredFindings = findings.filter(f => {
    if (filterMode === 'claims') return false;
    if (statusFilter !== 'all' && (f.support_status || '').toUpperCase() !== statusFilter) return false;
    return true;
  });

  const filteredClaims = claims.filter(c => {
    if (filterMode === 'findings') return false;
    if (statusFilter !== 'all') {
      const s = (c.support_status || '').toUpperCase();
      if (statusFilter === 'UNSUPPORTED') {
        if (s !== 'UNSUPPORTED' && s !== 'INSUFFICIENT_EVIDENCE') return false;
      } else if (s !== statusFilter) {
        return false;
      }
    }
    return true;
  });

  const getStatusBadge = (status) => {
    const s = (status || '').toUpperCase();
    if (s === 'SUPPORTED') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-950/60 border border-emerald-800/60 text-emerald-300">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          SUPPORTED
        </span>
      );
    }
    if (s === 'PARTIALLY_SUPPORTED') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-950/60 border border-amber-800/60 text-amber-300">
          <AlertCircle className="w-3 h-3 text-amber-400" />
          PARTIALLY SUPPORTED
        </span>
      );
    }
    if (s === 'INSUFFICIENT_EVIDENCE') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-rose-950/60 border border-rose-800/60 text-rose-300">
          <HelpCircle className="w-3 h-3 text-rose-400" />
          INSUFFICIENT EVIDENCE
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-rose-950/60 border border-rose-800/60 text-rose-300">
        <AlertCircle className="w-3 h-3 text-rose-400" />
        UNSUPPORTED
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Filtering Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-100">Findings & Evidence-Grounded Claims</h2>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Mode Selector */}
          <div className="inline-flex rounded-md border border-slate-700 p-0.5 bg-slate-950">
            <button
              type="button"
              onClick={() => setFilterMode('all')}
              className={`px-2.5 py-1 rounded transition-colors ${filterMode === 'all' ? 'bg-indigo-900 text-indigo-200 font-medium' : 'text-slate-400'}`}
            >
              All ({findings.length + claims.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('findings')}
              className={`px-2.5 py-1 rounded transition-colors ${filterMode === 'findings' ? 'bg-indigo-900 text-indigo-200 font-medium' : 'text-slate-400'}`}
            >
              Findings ({findings.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('claims')}
              className={`px-2.5 py-1 rounded transition-colors ${filterMode === 'claims' ? 'bg-indigo-900 text-indigo-200 font-medium' : 'text-slate-400'}`}
            >
              Claims ({claims.length})
            </button>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-300 text-xs focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="SUPPORTED">Supported Only</option>
              <option value="PARTIALLY_SUPPORTED">Partially Supported</option>
              <option value="UNSUPPORTED">Unsupported / Insufficient</option>
            </select>
          </div>
        </div>
      </div>

      {/* 2. Stage 4 Cross-Paper Findings Section */}
      {filteredFindings.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between pb-1 border-b border-slate-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400">
              Stage 4 Cross-Paper Findings ({filteredFindings.length})
            </h3>
            <span className="text-[11px] font-mono text-slate-500">Multi-study synthesis</span>
          </div>

          <div className="space-y-3">
            {filteredFindings.map((finding, idx) => (
              <div key={idx} className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">{finding.finding_id || `F00${idx + 1}`}</span>
                    <h4 className="text-sm font-semibold text-slate-100 leading-snug">{finding.finding_text}</h4>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                      {finding.finding_type || 'FINDING'}
                    </span>
                    {getStatusBadge(finding.support_status)}
                  </div>
                </div>

                {finding.explanation && (
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded border border-slate-800">
                    {finding.explanation}
                  </p>
                )}

                {/* Provenance Mapping */}
                <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60 text-xs">
                  <span className="text-[10px] font-mono text-slate-400">Provenance:</span>

                  {finding.claim_ids && finding.claim_ids.map((cid) => (
                    <button
                      key={cid}
                      type="button"
                      onClick={() => onEntityClick && onEntityClick('claim', cid)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-800 hover:bg-indigo-900 transition-colors"
                      title="Inspect Claim"
                    >
                      {cid}
                    </button>
                  ))}

                  {finding.evidence_ids && finding.evidence_ids.map((eid) => (
                    <button
                      key={eid}
                      type="button"
                      onClick={() => onEntityClick && onEntityClick('evidence', eid)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-950/80 text-sky-300 border border-sky-800 hover:bg-sky-900 transition-colors"
                      title="Inspect Evidence"
                    >
                      {eid}
                    </button>
                  ))}

                  {finding.paper_ids && finding.paper_ids.map((pid) => (
                    <button
                      key={pid}
                      type="button"
                      onClick={() => onEntityClick && onEntityClick('paper', pid)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-colors truncate max-w-[130px]"
                      title="Inspect Paper"
                    >
                      {pid}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 3. Stage 3 Research Claims Section */}
      {filteredClaims.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between pb-1 border-b border-slate-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-sky-400">
              Stage 3 Grounded Research Claims ({filteredClaims.length})
            </h3>
            <span className="text-[11px] font-mono text-slate-500">Atomic verified propositions</span>
          </div>

          <div className="space-y-3">
            {filteredClaims.map((claim, idx) => {
              const isUnsupported = (claim.support_status || '').toUpperCase() === 'UNSUPPORTED' || (claim.support_status || '').toUpperCase() === 'INSUFFICIENT_EVIDENCE';

              return (
                <div 
                  key={idx} 
                  className={`border rounded-lg p-5 shadow-sm space-y-3 ${
                    isUnsupported 
                      ? 'bg-rose-950/10 border-rose-900/40' 
                      : 'bg-slate-900 border-slate-800'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">{claim.claim_id || `C00${idx + 1}`}</span>
                      <h4 className="text-sm font-medium text-slate-100 leading-snug">{claim.claim_text}</h4>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                        {claim.claim_type || 'EMPIRICAL_FINDING'}
                      </span>
                      {getStatusBadge(claim.support_status)}
                    </div>
                  </div>

                  {isUnsupported && (
                    <div className="p-2.5 rounded bg-rose-950/30 border border-rose-900/40 text-xs text-rose-300">
                      Evidence was insufficient or contradictory to substantiate this claim within the retrieved literature.
                    </div>
                  )}

                  {claim.confidence_rationale && (
                    <div className="text-xs text-slate-400 leading-relaxed bg-slate-950/50 p-2.5 rounded border border-slate-800">
                      <strong className="text-slate-300">Grounding Rationale: </strong>
                      {claim.confidence_rationale}
                    </div>
                  )}

                  {/* Direct Excerpts / Quotes */}
                  {claim.exact_quotes && claim.exact_quotes.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono text-slate-400 uppercase">Direct Verbatim Excerpts:</span>
                      <div className="space-y-1">
                        {claim.exact_quotes.map((q, qi) => (
                          <blockquote key={qi} className="text-xs text-slate-300 italic border-l-2 border-indigo-500/60 pl-3 py-0.5 bg-slate-950/40">
                            "{q}"
                          </blockquote>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Evidence IDs & Source Papers */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60 text-xs">
                    <span className="text-[10px] font-mono text-slate-400">Linked Evidence:</span>
                    {claim.evidence_ids && claim.evidence_ids.length > 0 ? (
                      claim.evidence_ids.map((eid) => (
                        <button
                          key={eid}
                          type="button"
                          onClick={() => onEntityClick && onEntityClick('evidence', eid)}
                          className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-800 hover:bg-indigo-900 transition-colors"
                        >
                          {eid}
                        </button>
                      ))
                    ) : (
                      <span className="text-[11px] text-slate-500 italic">No evidence chunks linked</span>
                    )}

                    {claim.source_paper_ids && claim.source_paper_ids.length > 0 && (
                      <>
                        <span className="text-[10px] font-mono text-slate-400 ml-2">Source Papers:</span>
                        {claim.source_paper_ids.map((pid) => (
                          <button
                            key={pid}
                            type="button"
                            onClick={() => onEntityClick && onEntityClick('paper', pid)}
                            className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-colors truncate max-w-[130px]"
                          >
                            {pid}
                          </button>
                        ))}
                      </>
                    )}
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
