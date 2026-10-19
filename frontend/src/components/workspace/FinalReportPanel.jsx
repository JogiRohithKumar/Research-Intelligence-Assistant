import { useState } from 'react';
import { FileText, Copy, Check, Download, Quote } from 'lucide-react';
import SafeMarkdown from '../../utils/SafeMarkdown';
import EmptyState from './EmptyState';

export default function FinalReportPanel({
  reportMarkdown,
  citations = [],
  query,
  onEntityClick
}) {
  const [citationFormat, setCitationFormat] = useState('apa');
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [copiedAll, setCopiedAll] = useState(false);

  if (!reportMarkdown) {
    return (
      <EmptyState
        title="No Research Brief Available"
        message="The intelligence brief is compiled once research execution, cross-paper comparison, and citation verification conclude."
        iconType="search"
      />
    );
  }

  const handleCopyCitation = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleCopyAllCitations = () => {
    const formatted = citations.map(c => c[citationFormat] || c.apa || c.title).join('\n\n');
    navigator.clipboard.writeText(formatted);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  const handleDownloadReport = () => {
    const blob = new Blob([reportMarkdown], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `research_brief_${(query || 'synthesis').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 30)}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* 1. Report Actions & Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-2.5">
          <FileText className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-100">Academic Intelligence Brief</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadReport}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Markdown</span>
          </button>
        </div>
      </div>

      {/* 2. Main Sanitized Markdown Reader */}
      <article className="bg-slate-900 border border-slate-800 rounded-lg p-6 sm:p-8 shadow-sm">
        <SafeMarkdown content={reportMarkdown} onEntityClick={onEntityClick} />
      </article>

      {/* 3. Formal Academic Bibliography & Citation Formatter */}
      {citations.length > 0 && (
        <section className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Quote className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-slate-100">Bibliography & Formatted Citations</h3>
            </div>
            
            <div className="flex items-center gap-2">
              <div className="inline-flex rounded-md border border-slate-700 p-0.5 bg-slate-950">
                {['apa', 'ieee', 'mla', 'bibtex'].map((fmt) => (
                  <button
                    key={fmt}
                    type="button"
                    onClick={() => setCitationFormat(fmt)}
                    className={`px-2.5 py-1 text-xs font-mono uppercase rounded transition-colors ${
                      citationFormat === fmt
                        ? 'bg-indigo-900 text-indigo-200 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {fmt}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={handleCopyAllCitations}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-colors"
              >
                {copiedAll ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedAll ? 'Copied' : 'Copy All'}</span>
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {citations.map((c, i) => {
              const citationText = c[citationFormat] || c.apa || c.title || '';
              const isCopied = copiedIndex === i;

              return (
                <div key={i} className="bg-slate-950 p-3 rounded border border-slate-800 flex items-start justify-between gap-3 text-xs">
                  <div className="font-mono text-slate-300 leading-relaxed overflow-x-auto whitespace-pre-wrap select-all">
                    {citationText}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleCopyCitation(citationText, i)}
                    title="Copy citation"
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors shrink-0"
                  >
                    {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
