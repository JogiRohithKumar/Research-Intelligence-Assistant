import { useState } from 'react';
import { Search, Loader2, RotateCcw, BookOpen, Layers, User, Clock, Ban } from 'lucide-react';

export default function WorkspaceHeader({
  query,
  onSearch,
  loading,
  status,
  sessionId,
  iterationCount,
  maxIterations,
  groundingStatus,
  onReset,
  user = null,
  onOpenAuth = null,
  onLogout = null,
  onCancel = null,
  activeJobId = null
}) {
  const [inputQuery, setInputQuery] = useState(query || '');
  const [inputSessionId, setInputSessionId] = useState('');
  const [showSessionInput, setShowSessionInput] = useState(false);
  const [validationError, setValidationError] = useState('');

  const charCount = inputQuery.length;
  const maxChars = 1000;

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = inputQuery.trim();
    if (trimmed.length < 2) {
      setValidationError('Research question must be at least 2 characters.');
      return;
    }
    if (trimmed.length > maxChars) {
      setValidationError(`Research question exceeds maximum of ${maxChars} characters.`);
      return;
    }
    setValidationError('');
    onSearch(trimmed, inputSessionId.trim() || undefined);
  };

  // Determine real status badge
  const getStatusBadge = () => {
    if (status === 'QUEUED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/60 border border-amber-800/80 text-amber-300 text-xs font-mono font-medium animate-pulse">
          <Clock className="w-3.5 h-3.5" />
          QUEUED
        </span>
      );
    }
    if (status === 'RECONNECTING') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-950/60 border border-indigo-800/80 text-indigo-300 text-xs font-mono font-medium animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          RECONNECTING
        </span>
      );
    }
    if (loading || status === 'RUNNING' || status === 'RESEARCHING') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-sky-950/60 border border-sky-800/80 text-sky-300 text-xs font-mono font-medium animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          {status === 'QUEUED' ? 'QUEUED' : 'RESEARCHING'}
        </span>
      );
    }
    if (status === 'CANCELLED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-400 text-xs font-mono font-medium">
          <Ban className="w-3.5 h-3.5 text-slate-500" />
          CANCELLED
        </span>
      );
    }
    if (!status || status === 'idle') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-xs font-mono border border-slate-700">
          IDLE
        </span>
      );
    }
    const map = {
      SUFFICIENT: { bg: 'bg-emerald-950/50', border: 'border-emerald-800/60', text: 'text-emerald-300' },
      PARTIALLY_SUFFICIENT: { bg: 'bg-amber-950/50', border: 'border-amber-800/60', text: 'text-amber-300' },
      CONFLICTED: { bg: 'bg-rose-950/50', border: 'border-rose-800/60', text: 'text-rose-300' },
      NO_RELIABLE_EVIDENCE: { bg: 'bg-orange-950/50', border: 'border-orange-800/60', text: 'text-orange-300' },
      FAILED: { bg: 'bg-rose-950/70', border: 'border-rose-800', text: 'text-rose-400' },
      COMPLETED: { bg: 'bg-emerald-950/50', border: 'border-emerald-800/60', text: 'text-emerald-300' },
      completed: { bg: 'bg-emerald-950/50', border: 'border-emerald-800/60', text: 'text-emerald-300' },
      in_progress: { bg: 'bg-sky-950/50', border: 'border-sky-800/60', text: 'text-sky-300' }
    };
    const style = map[status] || { bg: 'bg-slate-800', border: 'border-slate-700', text: 'text-slate-300' };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded ${style.bg} border ${style.border} ${style.text} text-xs font-mono font-medium uppercase`}>
        {status}
      </span>
    );
  };

  const isJobActive = loading || status === 'QUEUED' || status === 'RUNNING' || status === 'RESEARCHING' || status === 'RECONNECTING';

  return (
    <header className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-4">
      {/* Top Banner: Brand, Authentication, and Status Metadata */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-indigo-950/60 border border-indigo-800/60 flex items-center justify-center text-indigo-400">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-100 tracking-tight">
                Research Intelligence Assistant
              </h1>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-400 border border-slate-700">
                V2
              </span>
            </div>
            <p className="text-xs text-slate-400">Scholarly Evidence Grounding & Cross-Paper Intelligence Workspace</p>
          </div>
        </div>

        {/* Real Status, Session Badges, and Auth */}
        <div className="flex flex-wrap items-center gap-2">
          {getStatusBadge()}

          {groundingStatus && (
            <span className={`px-2 py-0.5 rounded text-xs font-mono border ${
              groundingStatus === 'VERIFIED'
                ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-300'
                : groundingStatus === 'PARTIAL'
                ? 'bg-amber-950/40 border-amber-800/40 text-amber-300'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}>
              GROUNDING: {groundingStatus}
            </span>
          )}

          {iterationCount !== undefined && iterationCount > 0 && (
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 border border-slate-700 text-slate-300 flex items-center gap-1">
              <Layers className="w-3 h-3 text-slate-400" />
              Iter {iterationCount}{maxIterations ? `/${maxIterations}` : ''}
            </span>
          )}

          {sessionId && (
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800/60 border border-slate-700 text-slate-400 truncate max-w-[140px]" title={sessionId}>
              #{sessionId}
            </span>
          )}

          {activeJobId && (
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-950/40 border border-indigo-800/40 text-indigo-300 truncate max-w-[120px]" title={`Job ID: ${activeJobId}`}>
              job:{activeJobId.slice(0, 8)}
            </span>
          )}

          {/* User Profile / Auth State */}
          {user ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-200">
              <User className="w-3.5 h-3.5 text-indigo-400" />
              <span className="font-medium truncate max-w-[110px]" title={user.username || user.email}>
                {user.username || user.email}
              </span>
              {onLogout && (
                <button
                  type="button"
                  onClick={onLogout}
                  className="ml-1 text-slate-400 hover:text-rose-400 text-[11px] underline underline-offset-2 transition-colors"
                  title="Sign Out"
                >
                  Logout
                </button>
              )}
            </div>
          ) : (
            onOpenAuth && (
              <button
                type="button"
                onClick={onOpenAuth}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-indigo-600/80 hover:bg-indigo-600 text-white text-xs font-medium transition-colors"
                title="Sign in for persistent sessions"
              >
                <User className="w-3 h-3" />
                <span>Sign In</span>
              </button>
            )
          )}

          {onReset && (
            <button
              type="button"
              onClick={onReset}
              disabled={loading}
              title="Reset research session"
              className="p-1 rounded bg-slate-800/50 border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-40"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Query Form */}
      <form onSubmit={handleSubmit} className="space-y-2">
        <div className="relative">
          <textarea
            rows={2}
            value={inputQuery}
            onChange={(e) => {
              setInputQuery(e.target.value);
              if (validationError) setValidationError('');
            }}
            disabled={loading}
            placeholder="Enter a scientific research question (e.g. 'Coherence limits in superconducting fluxonium qubits')..."
            className="w-full bg-slate-950 border border-slate-800 rounded-md p-3 pr-24 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors disabled:opacity-50 resize-y"
          />
          <div className="absolute right-3 bottom-3 flex items-center gap-2">
            <span className={`text-[11px] font-mono ${charCount > maxChars ? 'text-rose-400' : 'text-slate-500'}`}>
              {charCount}/{maxChars}
            </span>
          </div>
        </div>

        {validationError && (
          <p className="text-xs text-rose-400 font-medium">{validationError}</p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowSessionInput(!showSessionInput)}
              className="text-xs text-slate-400 hover:text-slate-300 underline underline-offset-2 transition-colors"
            >
              {showSessionInput ? "Hide Session ID" : "Specify Session ID (Optional)"}
            </button>

            {showSessionInput && (
              <input
                type="text"
                value={inputSessionId}
                onChange={(e) => setInputSessionId(e.target.value)}
                placeholder="Custom session ID (e.g. session_123)"
                disabled={loading}
                className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono w-48"
              />
            )}
          </div>

          <div className="flex items-center gap-2">
            {isJobActive && onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded bg-rose-950/60 hover:bg-rose-900 border border-rose-800/80 text-rose-300 text-xs font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500/50"
                title="Cancel active research execution"
              >
                <Ban className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
            )}

            <button
              type="submit"
              disabled={loading || inputQuery.trim().length < 2 || charCount > maxChars}
              className="inline-flex items-center gap-2 px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-xs font-semibold tracking-wide transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>Execute Research</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </header>
  );
}
