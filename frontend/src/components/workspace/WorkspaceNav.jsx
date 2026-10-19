import { 
  Compass, 
  FileText, 
  CheckCircle, 
  Database, 
  BookOpen, 
  GitFork, 
  Table, 
  HelpCircle, 
  Activity 
} from 'lucide-react';

export default function WorkspaceNav({ activeTab, onSelectTab, counts }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Compass, count: null },
    { id: 'report', label: 'Research Brief', icon: FileText, count: null },
    { id: 'findings', label: 'Findings & Claims', icon: CheckCircle, count: (counts.findings || 0) + (counts.claims || 0) },
    { id: 'evidence', label: 'Evidence Matrix', icon: Database, count: counts.evidence || 0 },
    { id: 'sources', label: 'Sources', icon: BookOpen, count: counts.papers || 0 },
    { id: 'contradictions', label: 'Contradictions', icon: GitFork, count: counts.contradictions || 0 },
    { id: 'methodology', label: 'Methodology', icon: Table, count: counts.comparisons || 0 },
    { id: 'gaps', label: 'Research Gaps', icon: HelpCircle, count: counts.gaps || 0 },
    { id: 'trace', label: 'Research Trace', icon: Activity, count: counts.iterations || 0 },
  ];

  return (
    <nav aria-label="Workspace Sections" className="bg-slate-900 border border-slate-800 rounded-lg p-1.5 shadow-sm overflow-x-auto">
      <div className="flex items-center gap-1 min-w-max">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectTab(item.id)}
              className={`flex items-center gap-2 px-3 py-2 rounded text-xs font-medium transition-all ${
                isActive
                  ? 'bg-slate-800 text-indigo-300 border border-slate-700/80 shadow-xs'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
              <span>{item.label}</span>
              {item.count !== null && item.count > 0 && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                  isActive ? 'bg-indigo-950 text-indigo-300 border border-indigo-800' : 'bg-slate-800 text-slate-400'
                }`}>
                  {item.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
