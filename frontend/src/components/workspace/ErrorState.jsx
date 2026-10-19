import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function ErrorState({ error, onRetry }) {
  // Extract user-friendly error message safely without exposing internal trace
  let message = "An error occurred during research execution. Please verify your query and network connection.";
  if (typeof error === 'string') {
    message = error;
  } else if (error && typeof error === 'object' && error.message) {
    message = error.message;
  }

  return (
    <div className="p-6 bg-rose-950/20 border border-rose-900/50 rounded-lg text-slate-200 space-y-3">
      <div className="flex items-center gap-2.5 text-rose-400 font-semibold text-sm">
        <AlertTriangle className="w-5 h-5 shrink-0" />
        <span>Research Pipeline Error</span>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed font-mono bg-slate-900/60 p-3 rounded border border-rose-900/30">
        {message}
      </p>
      {onRetry && (
        <div className="pt-2">
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-rose-900/40 text-rose-200 border border-rose-800 hover:bg-rose-900/60 transition-colors focus:outline-none focus:ring-1 focus:ring-rose-500"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Research Execution</span>
          </button>
        </div>
      )}
    </div>
  );
}
