import { 
  ShieldCheck, 
  BookOpen, 
  Database, 
  CheckCircle2, 
  AlertCircle, 
  Layers, 
  GitFork, 
  HelpCircle,
  ArrowRight
} from 'lucide-react';
import EmptyState from './EmptyState';

export default function OverviewPanel({
  query,
  consensusSynthesis,
  groundedSummary,
  evidenceStrength,
  findings = [],
  claims = [],
  papers = [],
  evidenceChunks = [],
  contradictions = [],
  gaps = [],
  loopState,
  onNavigateTab,
  onEntityClick
}) {
  if (!query && papers.length === 0 && !consensusSynthesis && !groundedSummary) {
    return (
      <EmptyState
        title="No Research Session Active"
        message="Enter a scientific research query in the header above to initiate multi-source literature retrieval and grounded evidence synthesis."
        iconType="search"
      />
    );
  }

  // Consensus statement resolution
  const consensusText = consensusSynthesis?.synthesis_statement || groundedSummary || "No consensus synthesis statement generated for this session.";
  const consensusStatus = consensusSynthesis?.consensus_status || "EMERGING";
  const divergentPoints = consensusSynthesis?.divergent_points || [];

  // Support counts
  const supportedClaimsCount = claims.filter(c => (c.support_status || '').toUpperCase() === 'SUPPORTED').length;
  const unsupportedClaimsCount = claims.filter(c => (c.support_status || '').toUpperCase() === 'UNSUPPORTED' || (c.support_status || '').toUpperCase() === 'INSUFFICIENT_EVIDENCE').length;

  return (
    <div className="space-y-6">
      {/* 1. Research Question & Executive Synthesis Card */}
      <section className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Target Investigation</span>
            <h2 className="text-base font-semibold text-slate-100 mt-0.5">{query || "Scientific Query"}</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400">Consensus Status:</span>
            <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-medium border ${
              consensusStatus === 'ESTABLISHED'
                ? 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300'
                : consensusStatus === 'MIXED'
                ? 'bg-amber-950/50 border-amber-800/60 text-amber-300'
                : consensusStatus === 'INSUFFICIENT_EVIDENCE'
                ? 'bg-rose-950/50 border-rose-800/60 text-rose-300'
                : 'bg-indigo-950/50 border-indigo-800/60 text-indigo-300'
            }`}>
              {consensusStatus}
            </span>
          </div>
        </div>

        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-2">
            Executive Synthesis & Collective Finding
          </h3>
          <p className="text-sm text-slate-200 leading-relaxed bg-slate-950 p-4 rounded border border-slate-800">
            {consensusText}
          </p>
        </div>

        {divergentPoints.length > 0 && (
          <div className="pt-2">
            <h4 className="text-xs font-semibold text-amber-400 mb-2">Identified Divergences / Nuances:</h4>
            <ul className="space-y-1.5 text-xs text-slate-300 pl-4 list-disc">
              {divergentPoints.map((pt, i) => (
                <li key={i} className="leading-relaxed">{pt}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* 2. Qualitative Evidence Strength Evaluation */}
      {evidenceStrength && (
        <section className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-slate-100">Evidence Strength Assessment</h3>
            </div>
            <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold border ${
              evidenceStrength.rating === 'STRONG'
                ? 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300'
                : evidenceStrength.rating === 'MODERATE'
                ? 'bg-sky-950/50 border-sky-800/60 text-sky-300'
                : evidenceStrength.rating === 'MIXED'
                ? 'bg-amber-950/50 border-amber-800/60 text-amber-300'
                : 'bg-rose-950/50 border-rose-800/60 text-rose-300'
            }`}>
              RATING: {evidenceStrength.rating}
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded border border-slate-800">
            {evidenceStrength.rationale}
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Supporting Papers</span>
              <span className="text-sm font-semibold text-slate-200">{evidenceStrength.supporting_paper_count || 0}</span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Contradicting Papers</span>
              <span className="text-sm font-semibold text-slate-200">{evidenceStrength.contradicting_paper_count || 0}</span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Evidence Chunks</span>
              <span className="text-sm font-semibold text-slate-200">{evidenceStrength.evidence_chunks_count || 0}</span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Consistency</span>
              <span className="text-sm font-semibold text-slate-200 capitalize">{evidenceStrength.consistency_assessment || 'N/A'}</span>
            </div>
          </div>
          <p className="text-[10px] text-slate-500 italic">
            * Note: Strength assessed qualitatively within the retrieved literature corpus. Zero fabricated numeric confidence percentages.
          </p>
        </section>
      )}

      {/* 3. Real Empirical Metric Summary Grid */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('sources')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg text-left transition-colors"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <BookOpen className="w-3.5 h-3.5" />
            <span className="text-[10px] font-mono">Papers</span>
          </div>
          <span className="text-lg font-bold text-slate-100">{papers.length}</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('evidence')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg text-left transition-colors"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <Database className="w-3.5 h-3.5" />
            <span className="text-[10px] font-mono">Evidence</span>
          </div>
          <span className="text-lg font-bold text-slate-100">{evidenceChunks.length}</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('findings')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg text-left transition-colors"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-[10px] font-mono">Supported</span>
          </div>
          <span className="text-lg font-bold text-emerald-400">{supportedClaimsCount}</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('findings')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg text-left transition-colors"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-[10px] font-mono">Unsupported</span>
          </div>
          <span className="text-lg font-bold text-rose-400">{unsupportedClaimsCount}</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('contradictions')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg text-left transition-colors"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <GitFork className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[10px] font-mono">Contradictions</span>
          </div>
          <span className="text-lg font-bold text-amber-400">{contradictions.length}</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('gaps')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg text-left transition-colors"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[10px] font-mono">Gaps</span>
          </div>
          <span className="text-lg font-bold text-amber-400">{gaps.length}</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('trace')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg text-left transition-colors"
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <Layers className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-[10px] font-mono">Iterations</span>
          </div>
          <span className="text-lg font-bold text-sky-400">{loopState?.iterations?.length || 1}</span>
        </button>
      </section>

      {/* 4. Top Cross-Paper Findings Preview */}
      <section className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Key Verified Findings</h3>
            <p className="text-xs text-slate-400">Cross-study synthesized conclusions grounded in evidence</p>
          </div>
          {onNavigateTab && (
            <button
              type="button"
              onClick={() => onNavigateTab('findings')}
              className="text-xs text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1 font-medium"
            >
              <span>View All ({findings.length})</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>

        {findings.length === 0 ? (
          <p className="text-xs text-slate-400 italic">No cross-paper findings extracted for this query.</p>
        ) : (
          <div className="space-y-3">
            {findings.slice(0, 4).map((f, idx) => (
              <div key={idx} className="p-3.5 rounded bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-200">{f.finding_text}</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 shrink-0">
                    {f.finding_type || 'FINDING'}
                  </span>
                </div>
                {f.explanation && (
                  <p className="text-xs text-slate-400 leading-relaxed">{f.explanation}</p>
                )}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {f.evidence_ids && f.evidence_ids.map((eid) => (
                    <button
                      key={eid}
                      type="button"
                      onClick={() => onEntityClick && onEntityClick('evidence', eid)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-800 hover:bg-indigo-900 transition-colors"
                    >
                      {eid}
                    </button>
                  ))}
                  {f.paper_ids && f.paper_ids.map((pid) => (
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
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
