import { useState, useEffect, useRef } from 'react';
import WorkspaceHeader from './components/workspace/WorkspaceHeader';
import WorkspaceNav from './components/workspace/WorkspaceNav';
import OverviewPanel from './components/workspace/OverviewPanel';
import FinalReportPanel from './components/workspace/FinalReportPanel';
import FindingsClaimsPanel from './components/workspace/FindingsClaimsPanel';
import EvidenceExplorer from './components/workspace/EvidenceExplorer';
import SourceExplorer from './components/workspace/SourceExplorer';
import ContradictionPanel from './components/workspace/ContradictionPanel';
import MethodologyMatrix from './components/workspace/MethodologyMatrix';
import ResearchGapPanel from './components/workspace/ResearchGapPanel';
import ResearchTracePanel from './components/workspace/ResearchTracePanel';
import ProvenanceDrawer from './components/workspace/ProvenanceDrawer';
import ErrorState from './components/workspace/ErrorState';
import AuthModal from './components/workspace/AuthModal';
import LegalModal from './components/workspace/LegalModal';
import {
  submitResearchJob,
  getJobStatus,
  cancelResearchJob,
  subscribeJobStream,
  getSession,
  listSessions,
  getMe,
  logoutUser,
  getToken,
  removeToken
} from './services/api';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [lastQuery, setLastQuery] = useState('');
  const [lastSessionId, setLastSessionId] = useState('');
  const [selectedProvenanceEntity, setSelectedProvenanceEntity] = useState(null);

  // User and Auth State
  const [user, setUser] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Legal Modal State (Privacy Policy / Terms of Service)
  const [isLegalOpen, setIsLegalOpen] = useState(false);
  const [legalTab, setLegalTab] = useState('privacy');

  // Production Job & Real-time SSE State
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState('idle');
  const [liveLogs, setLiveLogs] = useState([]);
  const streamCleanupRef = useRef(null);

  // Initialize data from sessionStorage for session preservation across refreshes
  const [researchData, setResearchData] = useState(() => {
    try {
      const saved = sessionStorage.getItem('v2_research_session');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Verify and hydrate current user on mount
  useEffect(() => {
    let isMounted = true;
    async function initAuth() {
      const token = getToken();
      if (token) {
        try {
          const u = await getMe();
          if (isMounted) setUser(u);
        } catch {
          removeToken();
          if (isMounted) setUser(null);
        }
      }
    }
    initAuth();
    return () => {
      isMounted = false;
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
      }
    };
  }, []);

  const handleAuthSuccess = async (authUser) => {
    setUser(authUser);
    try {
      const sessionList = await listSessions();
      if (sessionList?.sessions?.length > 0) {
        const latestSessionSummary = sessionList.sessions[0];
        const fullSession = await getSession(latestSessionSummary.id);
        if (fullSession?.result_data) {
          setResearchData(fullSession.result_data);
          sessionStorage.setItem('v2_research_session', JSON.stringify(fullSession.result_data));
        }
      }
    } catch {
      // Continue with active state
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch (err) {
      console.warn("Logout error:", err);
    } finally {
      setUser(null);
    }
  };

  const pollJobStatus = (jobId, assignedSessionId) => {
    const interval = setInterval(async () => {
      try {
        const statusRes = await getJobStatus(jobId);
        if (statusRes.status === 'COMPLETED') {
          clearInterval(interval);
          setJobStatus('COMPLETED');
          setLoading(false);
          const sess = await getSession(assignedSessionId);
          if (sess?.result_data) {
            setResearchData(sess.result_data);
            sessionStorage.setItem('v2_research_session', JSON.stringify(sess.result_data));
          }
        } else if (statusRes.status === 'FAILED') {
          clearInterval(interval);
          setJobStatus('FAILED');
          setLoading(false);
          setError(statusRes.error_message || "Research job failed.");
        } else if (statusRes.status === 'CANCELLED') {
          clearInterval(interval);
          setJobStatus('CANCELLED');
          setLoading(false);
        } else {
          setJobStatus(statusRes.status);
        }
      } catch {
        // Continue polling until terminal status or user cancellation
      }
    }, 2500);
  };

  const handleSearch = async (queryText, sessionId) => {
    const token = getToken();
    if (!token && !user) {
      setIsAuthModalOpen(true);
      setError("Please sign in or create an account to execute research.");
      return;
    }

    setLoading(true);
    setError(null);
    setLastQuery(queryText);
    setLastSessionId(sessionId || '');
    setLiveLogs([]);
    setJobStatus('QUEUED');

    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }

    const idempotencyKey = `job_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    try {
      const jobRes = await submitResearchJob(queryText, sessionId, idempotencyKey);
      const jobId = jobRes.job_id;
      const assignedSessionId = jobRes.session_id || sessionId;
      setActiveJobId(jobId);
      setLastSessionId(assignedSessionId);
      setJobStatus(jobRes.status || 'QUEUED');

      if (jobRes.status === 'COMPLETED' && jobRes.result) {
        setResearchData(jobRes.result);
        sessionStorage.setItem('v2_research_session', JSON.stringify(jobRes.result));
        setJobStatus('COMPLETED');
        setLoading(false);
        setActiveTab('overview');
        return;
      }

      // Subscribe to real Server-Sent Events stream
      const cleanup = subscribeJobStream(
        jobId,
        async (evt) => {
          const { type, data } = evt;
          if (type === 'research_started') {
            setJobStatus('RUNNING');
          } else if (type === 'agent_log') {
            if (data) {
              setLiveLogs((prev) => [...prev, data.entry || data]);
            }
          } else if (type === 'research_completed') {
            setJobStatus('COMPLETED');
            setLoading(false);
            if (cleanup) cleanup();
            try {
              const sess = await getSession(assignedSessionId);
              if (sess?.result_data) {
                setResearchData(sess.result_data);
                sessionStorage.setItem('v2_research_session', JSON.stringify(sess.result_data));
              }
            } catch {
              // Retain current state
            }
            setActiveTab('overview');
          } else if (type === 'research_failed') {
            setJobStatus('FAILED');
            setLoading(false);
            if (cleanup) cleanup();
            setError(data?.error || data?.message || "Research job encountered an error during execution.");
          } else if (type === 'research_cancelled') {
            setJobStatus('CANCELLED');
            setLoading(false);
            if (cleanup) cleanup();
          }
        },
        (err) => {
          console.warn("SSE connection interrupted, initiating polling recovery:", err);
          setJobStatus('RECONNECTING');
          pollJobStatus(jobId, assignedSessionId);
        }
      );

      streamCleanupRef.current = cleanup;

    } catch (err) {
      console.error("Research execution failed:", err);
      let errorMsg = "Failed to complete research execution. Ensure the FastAPI backend server is accessible.";
      if (err.response?.status === 401) {
        errorMsg = "Authentication required. Please sign in to execute research.";
        setIsAuthModalOpen(true);
      } else if (err.response?.data?.error?.message) {
        errorMsg = err.response.data.error.message;
      } else if (err.response?.data?.detail) {
        errorMsg = err.response.data.detail;
      } else if (err.message) {
        errorMsg = err.message;
      }
      setError(errorMsg);
      setLoading(false);
      setJobStatus('FAILED');
    }
  };

  const handleCancel = async () => {
    if (!activeJobId) return;
    try {
      await cancelResearchJob(activeJobId);
    } catch (err) {
      console.warn("Cancellation error:", err);
    } finally {
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
        streamCleanupRef.current = null;
      }
      setJobStatus('CANCELLED');
      setLoading(false);
    }
  };

  const handleReset = () => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setResearchData(null);
    setError(null);
    setSelectedProvenanceEntity(null);
    setActiveJobId(null);
    setJobStatus('idle');
    setLiveLogs([]);
    sessionStorage.removeItem('v2_research_session');
  };

  const handleEntityClick = (type, id) => {
    if (!type || !id) return;
    setSelectedProvenanceEntity({ type, id });
  };

  // Derive counts from authoritative backend state
  const papers = researchData?.papers || [];
  const evidenceChunks = researchData?.evidence_registry || [];
  const findings = researchData?.cross_paper_findings || researchData?.intelligence?.findings || [];
  const claims = researchData?.claims || [];
  const contradictions = researchData?.contradiction_findings || researchData?.intelligence?.contradictions || [];
  const comparisons = researchData?.study_comparisons || researchData?.intelligence?.comparisons || [];
  const gaps = researchData?.research_gaps || researchData?.intelligence?.gaps || [];
  const actionableGaps = researchData?.actionable_gaps || [];
  const consensusSynthesis = researchData?.consensus_synthesis || researchData?.intelligence?.consensus || null;
  const evidenceStrength = researchData?.evidence_strength || researchData?.intelligence?.evidence_strength || null;
  const loopState = researchData?.loop_state || null;
  const iterationsHistory = researchData?.iterations_history || [];
  const persistedAgentLogs = researchData?.agent_logs || [];
  const combinedAgentLogs = [...persistedAgentLogs, ...liveLogs];
  const reportMarkdown = researchData?.report || researchData?.grounded_summary || "";
  const citations = researchData?.citations || [];

  const counts = {
    papers: papers.length,
    evidence: evidenceChunks.length,
    findings: findings.length,
    claims: claims.length,
    contradictions: contradictions.length,
    comparisons: comparisons.length,
    gaps: gaps.length > 0 ? gaps.length : actionableGaps.length,
    iterations: loopState?.iterations?.length || iterationsHistory.length || (researchData ? 1 : 0),
  };

  // Derive active status honestly
  const currentStatus = loading
    ? (jobStatus !== 'idle' ? jobStatus : 'RESEARCHING')
    : researchData?.sufficiency_evaluation?.status || researchData?.execution_status || jobStatus || 'idle';

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-200 p-4 sm:p-6 md:p-8 font-sans selection:bg-indigo-500/30">
      <div className="max-w-[1500px] mx-auto space-y-5">
        {/* Workspace Top Header & Query Input */}
        <WorkspaceHeader
          query={researchData?.query || ""}
          onSearch={handleSearch}
          loading={loading}
          status={currentStatus}
          sessionId={researchData?.thread_id || lastSessionId}
          iterationCount={counts.iterations}
          maxIterations={researchData?.max_iterations || 3}
          groundingStatus={researchData?.grounding_status || researchData?.citation_verification?.grounding_status}
          onReset={handleReset}
          user={user}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onLogout={handleLogout}
          onCancel={handleCancel}
          activeJobId={activeJobId}
        />

        {/* Error State Banner */}
        {error && (
          <ErrorState
            error={error}
            onRetry={() => lastQuery && handleSearch(lastQuery, lastSessionId)}
          />
        )}

        {/* Section Navigation Tabs */}
        <WorkspaceNav
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          counts={counts}
        />

        {/* Active Workspace View Panel */}
        <main className="min-h-[500px]">
          {activeTab === 'overview' && (
            <OverviewPanel
              query={researchData?.query}
              consensusSynthesis={consensusSynthesis}
              groundedSummary={researchData?.grounded_summary}
              evidenceStrength={evidenceStrength}
              findings={findings}
              claims={claims}
              papers={papers}
              evidenceChunks={evidenceChunks}
              contradictions={contradictions}
              gaps={gaps}
              loopState={loopState}
              onNavigateTab={setActiveTab}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'report' && (
            <FinalReportPanel
              reportMarkdown={reportMarkdown}
              citations={citations}
              query={researchData?.query}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'findings' && (
            <FindingsClaimsPanel
              findings={findings}
              claims={claims}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'evidence' && (
            <EvidenceExplorer
              evidenceChunks={evidenceChunks}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'sources' && (
            <SourceExplorer
              papers={papers}
              evidenceChunks={evidenceChunks}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'contradictions' && (
            <ContradictionPanel
              contradictions={contradictions}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'methodology' && (
            <MethodologyMatrix
              comparisons={comparisons}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'gaps' && (
            <ResearchGapPanel
              gaps={gaps}
              actionableGaps={actionableGaps}
              onEntityClick={handleEntityClick}
            />
          )}

          {activeTab === 'trace' && (
            <ResearchTracePanel
              loopState={loopState}
              iterationsHistory={iterationsHistory}
              agentLogs={combinedAgentLogs}
              onEntityClick={handleEntityClick}
            />
          )}
        </main>
      </div>

      {/* Production Workspace Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/60 px-6 py-3 text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2 mt-auto">
        <div className="flex items-center space-x-2 text-[11px]">
          <span className="font-medium text-slate-400">Research Intelligence Assistant</span>
          <span>•</span>
          <span>Autonomous Evidence Synthesis</span>
        </div>
        <div className="flex items-center space-x-4 text-[11px]">
          <button
            id="footer-privacy-btn"
            onClick={() => { setLegalTab('privacy'); setIsLegalOpen(true); }}
            className="hover:text-slate-300 transition-colors underline focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            Privacy Policy
          </button>
          <span>•</span>
          <button
            id="footer-terms-btn"
            onClick={() => { setLegalTab('terms'); setIsLegalOpen(true); }}
            className="hover:text-slate-300 transition-colors underline focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            Terms of Service
          </button>
        </div>
      </footer>

      {/* Provenance Inspection Drawer */}
      <ProvenanceDrawer
        selectedEntity={selectedProvenanceEntity}
        onClose={() => setSelectedProvenanceEntity(null)}
        findings={findings}
        claims={claims}
        evidenceChunks={evidenceChunks}
        papers={papers}
        onSelectEntity={handleEntityClick}
      />

      {/* Authentication & User Account Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />

      {/* Privacy Policy & Terms of Service Dialog */}
      <LegalModal
        isOpen={isLegalOpen}
        initialTab={legalTab}
        onClose={() => setIsLegalOpen(false)}
      />
    </div>
  );
}