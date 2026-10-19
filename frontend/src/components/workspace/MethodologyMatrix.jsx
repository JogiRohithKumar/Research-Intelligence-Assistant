import { Table } from 'lucide-react';
import EmptyState from './EmptyState';

export default function MethodologyMatrix({
  comparisons = [],
  onEntityClick
}) {
  if (comparisons.length === 0) {
    return (
      <EmptyState
        title="No Methodology Comparison Data Extracted"
        message="Structured methodology dimensions (dataset, sample size, intervention, metrics) are populated when explicitly observed in retrieved excerpts."
        iconType="inbox"
      />
    );
  }

  const renderValue = (val) => {
    if (!val || typeof val !== 'string' || val.trim() === '') {
      return <span className="text-slate-600 font-mono">—</span>;
    }
    return <span className="text-slate-200">{val}</span>;
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Table className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-100">
            Cross-Study Methodology Comparison Matrix ({comparisons.length} studies)
          </h2>
        </div>
        <p className="text-xs text-slate-400 hidden sm:block">
          Explicitly extracted dimensions; missing parameters preserved as unobserved
        </p>
      </div>

      {/* Responsive Table Container */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 border-b border-slate-800 text-[11px] font-mono uppercase text-slate-400 tracking-wider">
                <th className="p-3 font-semibold min-w-[200px]">Study / Paper</th>
                <th className="p-3 font-semibold min-w-[140px]">Population</th>
                <th className="p-3 font-semibold min-w-[140px]">Dataset / Corpus</th>
                <th className="p-3 font-semibold min-w-[100px]">Sample Size</th>
                <th className="p-3 font-semibold min-w-[160px]">Intervention / Method</th>
                <th className="p-3 font-semibold min-w-[140px]">Baseline / Control</th>
                <th className="p-3 font-semibold min-w-[150px]">Primary Outcomes</th>
                <th className="p-3 font-semibold min-w-[120px]">Metrics</th>
                <th className="p-3 font-semibold min-w-[160px]">Limitations</th>
                <th className="p-3 font-semibold min-w-[100px]">Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {comparisons.map((comp, idx) => (
                <tr key={comp.paper_id || idx} className="hover:bg-slate-850/50 transition-colors">
                  <td className="p-3 align-top font-medium">
                    <button
                      type="button"
                      onClick={() => onEntityClick && onEntityClick('paper', comp.paper_id)}
                      className="text-left text-indigo-300 hover:text-indigo-200 underline underline-offset-2 leading-snug"
                    >
                      {comp.paper_title || comp.paper_id}
                    </button>
                    <span className="block text-[10px] font-mono text-slate-500 mt-0.5">
                      {comp.paper_id}
                    </span>
                  </td>
                  <td className="p-3 align-top">{renderValue(comp.population)}</td>
                  <td className="p-3 align-top">{renderValue(comp.dataset)}</td>
                  <td className="p-3 align-top font-mono">{renderValue(comp.sample_size)}</td>
                  <td className="p-3 align-top">{renderValue(comp.intervention_or_method)}</td>
                  <td className="p-3 align-top">{renderValue(comp.baseline_or_control)}</td>
                  <td className="p-3 align-top">{renderValue(comp.outcomes)}</td>
                  <td className="p-3 align-top font-mono">{renderValue(comp.metrics)}</td>
                  <td className="p-3 align-top text-slate-400">{renderValue(comp.limitations)}</td>
                  <td className="p-3 align-top">
                    {comp.evidence_ids && comp.evidence_ids.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {comp.evidence_ids.map((eid) => (
                          <button
                            key={eid}
                            type="button"
                            onClick={() => onEntityClick && onEntityClick('evidence', eid)}
                            className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-950 text-sky-300 border border-sky-800 hover:bg-sky-900"
                          >
                            {eid}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-600 font-mono">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
