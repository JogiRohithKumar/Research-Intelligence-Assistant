import { useState } from 'react';
import { Database, Search, Copy, Check, ExternalLink, Filter } from 'lucide-react';
import EmptyState from './EmptyState';

export default function EvidenceExplorer({
  evidenceChunks = [],
  onEntityClick
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [providerFilter, setProviderFilter] = useState('all');
  const [copiedId, setCopiedId] = useState(null);

  if (evidenceChunks.length === 0) {
    return (
      <EmptyState
        title="No Evidence Chunks Ingested"
        message="Evidence chunks are extracted and indexed during the RAG ingestion stage."
        iconType="inbox"
      />
    );
  }

  const handleCopyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredChunks = evidenceChunks.filter((chunk) => {
    if (providerFilter !== 'all' && (chunk.provider || '').toLowerCase() !== providerFilter.toLowerCase()) {
      return false;
    }
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const matchesText = (chunk.text || '').toLowerCase().includes(term);
    const matchesId = (chunk.evidence_id || '').toLowerCase().includes(term);
    const matchesTitle = (chunk.title || '').toLowerCase().includes(term);
    const matchesPaperId = (chunk.paper_id || '').toLowerCase().includes(term);
    return matchesText || matchesId || matchesTitle || matchesPaperId;
  });

  return (
    <div className="space-y-6">
      {/* 1. Header & Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100">
            Evidence Registry ({evidenceChunks.length} chunks)
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter by keyword, ID, paper..."
              className="bg-slate-950 border border-slate-800 rounded pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-56"
            />
          </div>

          {/* Provider Filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1.5 text-slate-300 text-xs focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Providers</option>
              <option value="arxiv">arXiv</option>
              <option value="local_corpus">Local Corpus</option>
            </select>
          </div>
        </div>
      </div>

      {/* 2. Evidence Cards List */}
      {filteredChunks.length === 0 ? (
        <p className="text-xs text-slate-400 italic text-center py-8">
          No evidence chunks match the current search filter.
        </p>
      ) : (
        <div className="space-y-4">
          {filteredChunks.map((chunk, idx) => {
            const isCopied = copiedId === chunk.evidence_id;

            return (
              <div 
                key={chunk.evidence_id || idx} 
                className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-3"
              >
                {/* Meta Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800/80">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-sky-950 text-sky-300 border border-sky-800">
                      {chunk.evidence_id || `E00${idx + 1}`}
                    </span>
                    <button
                      type="button"
                      onClick={() => onEntityClick && onEntityClick('paper', chunk.paper_id)}
                      className="text-xs font-medium text-slate-200 hover:text-indigo-300 transition-colors truncate max-w-sm"
                      title={chunk.title || chunk.paper_id}
                    >
                      {chunk.title || chunk.paper_id}
                    </button>
                    {chunk.year && (
                      <span className="text-xs text-slate-400">({chunk.year})</span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 uppercase">
                      {chunk.provider || 'arxiv'}
                    </span>
                    {chunk.retrieval_score !== undefined && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-sky-300">
                        Score: {typeof chunk.retrieval_score === 'number' ? chunk.retrieval_score.toFixed(3) : chunk.retrieval_score}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => handleCopyText(chunk.text, chunk.evidence_id)}
                      title="Copy excerpt text"
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                    >
                      {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Verbatim Excerpt Text */}
                <div className="bg-slate-950 p-4 rounded border border-slate-800/80">
                  <blockquote className="text-sm text-slate-200 font-sans leading-relaxed whitespace-pre-wrap select-text">
                    "{chunk.text}"
                  </blockquote>
                </div>

                {/* Provenance & Location Metadata Footer */}
                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 font-mono pt-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <span>
                      <strong>Section:</strong> {chunk.section || 'Abstract / Unspecified'}
                    </span>
                    {chunk.page && (
                      <span>
                        <strong>Page:</strong> {chunk.page}
                      </span>
                    )}
                    <span>
                      <strong>Source Type:</strong> {chunk.evidence_source_type || 'indexed_abstract'}
                    </span>
                    <span className="truncate max-w-[200px]" title={chunk.chunk_id}>
                      <strong>Chunk:</strong> {chunk.chunk_id || 'N/A'}
                    </span>
                  </div>

                  {chunk.source_url && (
                    <a
                      href={chunk.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      <span>Open Source</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
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
