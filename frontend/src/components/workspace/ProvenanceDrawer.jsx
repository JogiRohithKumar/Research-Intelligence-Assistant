import { useEffect } from 'react';
import { X, ExternalLink, ArrowRight } from 'lucide-react';
import { formatAuthors, sanitizeUrl } from '../../utils/sanitize';

export default function ProvenanceDrawer({
  selectedEntity,
  onClose,
  findings = [],
  claims = [],
  evidenceChunks = [],
  papers = [],
  onSelectEntity
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!selectedEntity || !selectedEntity.id) return null;

  const { type, id } = selectedEntity;

  // Resolve matching entity
  let currentFinding = null;
  let currentClaim = null;
  let currentEvidence = null;
  let currentPaper = null;

  if (type === 'finding') {
    currentFinding = findings.find(f => f.finding_id === id) || null;
  } else if (type === 'claim') {
    currentClaim = claims.find(c => c.claim_id === id) || null;
  } else if (type === 'evidence') {
    currentEvidence = evidenceChunks.find(e => e.evidence_id === id || e.chunk_id === id) || null;
  } else if (type === 'paper') {
    currentPaper = papers.find(p => p.paper_id === id || p.id === id) || null;
  }

  // Linked relationships
  let relatedFindings = [];
  let relatedClaims = [];
  let relatedEvidence = [];
  let relatedPapers = [];

  if (currentFinding) {
    relatedClaims = claims.filter(c => (currentFinding.claim_ids || []).includes(c.claim_id));
    relatedEvidence = evidenceChunks.filter(e => (currentFinding.evidence_ids || []).includes(e.evidence_id));
    relatedPapers = papers.filter(p => (currentFinding.paper_ids || []).includes(p.paper_id || p.id));
  } else if (currentClaim) {
    relatedFindings = findings.filter(f => (f.claim_ids || []).includes(currentClaim.claim_id));
    relatedEvidence = evidenceChunks.filter(e => (currentClaim.evidence_ids || []).includes(e.evidence_id));
    relatedPapers = papers.filter(p => (currentClaim.source_paper_ids || []).includes(p.paper_id || p.id));
  } else if (currentEvidence) {
    relatedClaims = claims.filter(c => (c.evidence_ids || []).includes(currentEvidence.evidence_id));
    relatedFindings = findings.filter(f => (f.evidence_ids || []).includes(currentEvidence.evidence_id));
    currentPaper = papers.find(p => (p.paper_id === currentEvidence.paper_id || p.id === currentEvidence.paper_id)) || null;
    if (currentPaper) relatedPapers = [currentPaper];
  } else if (currentPaper) {
    const pid = currentPaper.paper_id || currentPaper.id;
    relatedEvidence = evidenceChunks.filter(e => e.paper_id === pid);
    relatedClaims = claims.filter(c => (c.source_paper_ids || []).includes(pid));
    relatedFindings = findings.filter(f => (f.paper_ids || []).includes(pid));
  }

  return (
    <div 
      role="dialog" 
      aria-label="Provenance Inspector" 
      className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
        <div className="space-y-0.5">
          <span className="text-[10px] font-mono uppercase text-indigo-400">Provenance Inspector</span>
          <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <span className="capitalize">{type}:</span>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {id}
            </span>
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close inspector"
          className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Chain Trace View */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs">
        {/* Navigation Breadcrumb Chain */}
        <div className="p-3 rounded bg-slate-950 border border-slate-800 space-y-2">
          <span className="text-[10px] font-mono uppercase text-slate-500 block">End-to-End Grounding Chain</span>
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 flex-wrap">
            <span className={type === 'finding' ? 'text-indigo-300 font-bold' : ''}>Finding</span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className={type === 'claim' ? 'text-indigo-300 font-bold' : ''}>Claim</span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className={type === 'evidence' ? 'text-indigo-300 font-bold' : ''}>Evidence</span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className={type === 'paper' ? 'text-indigo-300 font-bold' : ''}>Paper</span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span>Source</span>
          </div>
        </div>

        {/* Selected Entity Details */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Current Entity Details
          </h3>

          {currentFinding && (
            <div className="bg-slate-950 p-4 rounded border border-slate-800 space-y-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase">{currentFinding.finding_type}</span>
              <h4 className="text-sm font-semibold text-slate-100">{currentFinding.finding_text}</h4>
              {currentFinding.explanation && (
                <p className="text-slate-300 leading-relaxed">{currentFinding.explanation}</p>
              )}
            </div>
          )}

          {currentClaim && (
            <div className="bg-slate-950 p-4 rounded border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-indigo-400 uppercase">{currentClaim.claim_type}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase">
                  {currentClaim.support_status}
                </span>
              </div>
              <h4 className="text-sm font-semibold text-slate-100">{currentClaim.claim_text}</h4>
              {currentClaim.confidence_rationale && (
                <p className="text-slate-300 leading-relaxed">{currentClaim.confidence_rationale}</p>
              )}
            </div>
          )}

          {currentEvidence && (
            <div className="bg-slate-950 p-4 rounded border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>Provider: {currentEvidence.provider}</span>
                {currentEvidence.retrieval_score !== undefined && (
                  <span>Score: {Number(currentEvidence.retrieval_score).toFixed(3)}</span>
                )}
              </div>
              <blockquote className="p-3 bg-slate-900 rounded border border-slate-800 text-slate-200 leading-relaxed italic">
                "{currentEvidence.text}"
              </blockquote>
              <div className="text-[11px] text-slate-400 space-y-0.5 font-mono">
                <div>Section: {currentEvidence.section || 'Abstract'}</div>
                <div>Chunk ID: {currentEvidence.chunk_id}</div>
              </div>
            </div>
          )}

          {currentPaper && (
            <div className="bg-slate-950 p-4 rounded border border-slate-800 space-y-3">
              <h4 className="text-sm font-semibold text-slate-100">{currentPaper.title}</h4>
              <p className="text-slate-400">{formatAuthors(currentPaper.authors)} ({currentPaper.year || 'N/A'})</p>
              {currentPaper.abstract && (
                <p className="text-slate-300 leading-relaxed line-clamp-4">{currentPaper.abstract}</p>
              )}
              {currentPaper.paper_url && (
                <a
                  href={sanitizeUrl(currentPaper.paper_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300"
                >
                  <span>Open Primary Source URL</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          )}
        </div>

        {/* Upstream/Downstream Connected Entities */}
        <div className="space-y-4 pt-3 border-t border-slate-800">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Connected Provenance Links
          </h3>

          {/* Related Findings */}
          {relatedFindings.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono uppercase text-slate-400">Associated Findings:</span>
              <div className="space-y-1.5">
                {relatedFindings.map((f, fi) => (
                  <button
                    key={fi}
                    type="button"
                    onClick={() => onSelectEntity && onSelectEntity('finding', f.finding_id)}
                    className="w-full text-left p-2.5 rounded bg-slate-950 hover:bg-slate-800/80 border border-slate-800 transition-colors"
                  >
                    <span className="font-mono text-[10px] text-indigo-400 block">{f.finding_id}</span>
                    <span className="text-slate-200 block text-xs truncate">{f.finding_text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Related Claims */}
          {relatedClaims.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono uppercase text-slate-400">Associated Claims:</span>
              <div className="space-y-1.5">
                {relatedClaims.map((c, ci) => (
                  <button
                    key={ci}
                    type="button"
                    onClick={() => onSelectEntity && onSelectEntity('claim', c.claim_id)}
                    className="w-full text-left p-2.5 rounded bg-slate-950 hover:bg-slate-800/80 border border-slate-800 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-sky-400">{c.claim_id}</span>
                      <span className="text-[10px] font-mono text-slate-400 uppercase">{c.support_status}</span>
                    </div>
                    <span className="text-slate-200 block text-xs truncate">{c.claim_text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Related Evidence Chunks */}
          {relatedEvidence.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono uppercase text-slate-400">Associated Evidence Chunks:</span>
              <div className="space-y-1.5">
                {relatedEvidence.map((e, ei) => (
                  <button
                    key={ei}
                    type="button"
                    onClick={() => onSelectEntity && onSelectEntity('evidence', e.evidence_id)}
                    className="w-full text-left p-2.5 rounded bg-slate-950 hover:bg-slate-800/80 border border-slate-800 transition-colors"
                  >
                    <span className="font-mono text-[10px] text-sky-400 block">{e.evidence_id}</span>
                    <span className="text-slate-200 block text-xs truncate">"{e.text}"</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Related Papers */}
          {relatedPapers.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono uppercase text-slate-400">Associated Literature Papers:</span>
              <div className="space-y-1.5">
                {relatedPapers.map((p, pi) => (
                  <button
                    key={pi}
                    type="button"
                    onClick={() => onSelectEntity && onSelectEntity('paper', p.paper_id || p.id)}
                    className="w-full text-left p-2.5 rounded bg-slate-950 hover:bg-slate-800/80 border border-slate-800 transition-colors"
                  >
                    <span className="font-mono text-[10px] text-slate-400 block">{p.paper_id || p.id}</span>
                    <span className="text-slate-200 block text-xs truncate">{p.title}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
