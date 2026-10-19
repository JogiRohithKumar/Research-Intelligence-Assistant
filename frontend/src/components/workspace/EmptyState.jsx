import { Inbox, AlertCircle, FileSearch, ShieldCheck } from 'lucide-react';

export default function EmptyState({ 
  title = "No Data Available", 
  message = "No records were found for this section in the current research session.",
  iconType = "inbox"
}) {
  const IconComponent = {
    inbox: Inbox,
    search: FileSearch,
    shield: ShieldCheck,
    alert: AlertCircle
  }[iconType] || Inbox;

  return (
    <div className="py-12 px-6 flex flex-col items-center justify-center text-center bg-slate-900/40 border border-slate-800 rounded-lg">
      <div className="w-12 h-12 rounded-lg bg-slate-800/80 border border-slate-700/60 flex items-center justify-center mb-3">
        <IconComponent className="w-6 h-6 text-slate-400" />
      </div>
      <h3 className="text-sm font-semibold text-slate-200 mb-1">{title}</h3>
      <p className="text-xs text-slate-400 max-w-md leading-relaxed">{message}</p>
    </div>
  );
}
