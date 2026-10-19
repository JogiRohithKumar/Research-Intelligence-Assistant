import { useState } from 'react';
import { BookOpen, ExternalLink, ChevronDown, ChevronUp, Search, Database } from 'lucide-react';
import { formatAuthors, sanitizeUrl } from '../../utils/sanitize';
import EmptyState from './EmptyState';

export default function SourceExplorer({
  papers = [],
  evidenceChunks = [],
  onEntityClick
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedPaperIds, setExpandedPaperIds] = useState(new Set());

  if (papers.length === 0) {
    return (
      <EmptyState
        title="No Literature Retrieved"
        message="Scholarly literature papers are retrieved from arXiv and academic providers based on the generated search plan."
        iconType="inbox"
      />
    );
  }

  const toggleExpand = (id) => {
    setExpandedPaperIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Build mapping from paper_id to evidence chunks
  const paperEvidenceMap = {};
  evidenceChunks.forEach((chunk) => {
    const pid = chunk.paper_id;
    if (!paperEvidenceMap[pid]) paperEvidenceMap[pid] = [];
    paperEvidenceMap[pid].push(chunk);
  });

  const filteredPapers = papers.filter((p) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const titleMatch = (p.title || '').toLowerCase().includes(term);
    const authorMatch = Array.isArray(p.authors) && p.authors.some(a => a.toLowerCase().includes(term));
    const idMatch = (p.paper_id || p.id || '').toLowerCase().includes(term);
    return titleMatch || authorMatch || idMatch;
  });

  return (
    <div className="space-y-6">
      {/* 1. Header & Search Filter */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-100">
            Source Literature ({papers.length} papers retrieved)
          </h2>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search papers by title or author..."
            className="bg-slate-950 border border-slate-800 rounded pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-64"
          />
        </div>
      </div>

      {/* 2. Paper Cards */}
      {filteredPapers.length === 0 ? (
        <p className="text-xs text-slate-400 italic text-center py-8">
          No papers match your search query.
        </p>
      ) : (
        <div className="space-y-4">
          {filteredPapers.map((paper, idx) => {
            const paperId = paper.paper_id || paper.id || `paper-${idx}`;
            const isExpanded = expandedPaperIds.has(paperId);
            const associatedEvidence = paperEvidenceMap[paperId] || paperEvidenceMap[paper.id] || [];
            const safeSourceUrl = sanitizeUrl(paper.paper_url);
            
            // Format DOI safely
            const rawDoi = paper.doi ? paper.doi.trim() : null;
            const doiUrl = rawDoi 
              ? (rawDoi.startsWith('http') ? sanitizeUrl(rawDoi) : `https://doi.org/${encodeURIComponent(rawDoi)}`) 
              : null;

            return (
              <div 
                key={paperId} 
                className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-3"
              >
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="space-y-1">
                    <h3 className="text-sm font-semibold text-slate-100 leading-snug">
                      {paper.title || "Untitled Paper"}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {formatAuthors(paper.authors)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 text-xs font-mono">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                      {paper.source || paper.provider || 'arxiv'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {paper.year || (paper.published ? new Date(paper.published).getFullYear() : 'Year unavailable')}
                    </span>
                    {paper.relevance_score !== undefined && paper.relevance_score > 0 && (
                      <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                        Rel: {paper.relevance_score.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Metadata & Links Bar */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1 border-t border-slate-800/80">
                  {doiUrl ? (
                    <a
                      href={doiUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      <span>DOI: {rawDoi}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-slate-500 italic">DOI unavailable</span>
                  )}

                  {safeSourceUrl ? (
                    <a
                      href={safeSourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-slate-300 hover:text-indigo-300 transition-colors"
                    >
                      <span>Repository Source</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-slate-500 italic">Source URL unavailable</span>
                  )}

                  <span className="text-slate-500 font-mono text-[11px]">
                    ID: {paperId}
                  </span>
                </div>

                {/* Abstract Section */}
                {paper.abstract ? (
                  <div className="space-y-1.5 pt-1">
                    <button
                      type="button"
                      onClick={() => toggleExpand(paperId)}
                      className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      <span>{isExpanded ? 'Collapse Abstract' : 'View Abstract'}</span>
                    </button>

                    {isExpanded && (
                      <div className="bg-slate-950 p-3.5 rounded border border-slate-800 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap select-text">
                        {paper.abstract}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">Abstract unavailable for this record.</p>
                )}

                {/* Associated Evidence Count & Badges */}
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/60 text-xs">
                  <div className="flex items-center gap-1 text-slate-400">
                    <Database className="w-3.5 h-3.5 text-sky-400" />
                    <span>Evidence Chunks ({associatedEvidence.length}):</span>
                  </div>

                  {associatedEvidence.length === 0 ? (
                    <span className="text-[11px] text-slate-500 italic">No evidence chunks ingested from this paper</span>
                  ) : (
                    associatedEvidence.map((chunk) => (
                      <button
                        key={chunk.evidence_id}
                        type="button"
                        onClick={() => onEntityClick && onEntityClick('evidence', chunk.evidence_id)}
                        className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-950/80 text-sky-300 border border-sky-800 hover:bg-sky-900 transition-colors"
                        title={chunk.text ? chunk.text.slice(0, 100) : 'View evidence'}
                      >
                        {chunk.evidence_id}
                      </button>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
