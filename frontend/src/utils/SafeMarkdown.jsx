import { Fragment } from 'react';

/**
 * Tokenizes text to identify citation references like [E001], [C001], [F001], [P1], etc.
 * and renders them as clickable badges.
 */
function renderTextWithCitations(text, onEntityClick) {
  if (!text || typeof text !== 'string') return null;

  const tokenRegex = /\[(E\d{3,4}|C\d{3,4}|F\d{3,4}|CT\d{3,4}|G\d{3,4}|arxiv:[^\]\s]+)\]/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = tokenRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[1];
    let type = 'unknown';
    if (token.startsWith('E')) type = 'evidence';
    else if (token.startsWith('C')) type = 'claim';
    else if (token.startsWith('F')) type = 'finding';
    else if (token.startsWith('CT')) type = 'contradiction';
    else if (token.startsWith('G')) type = 'gap';
    else if (token.startsWith('arxiv:')) type = 'paper';

    parts.push(
      <button
        key={`token-${match.index}`}
        type="button"
        onClick={() => onEntityClick && onEntityClick(type, token)}
        className="inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-mono font-medium rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/20 hover:text-indigo-200 transition-colors focus:outline-none focus:ring-1 focus:ring-indigo-400"
        title={`Inspect ${type}: ${token}`}
      >
        {token}
      </button>
    );

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}

/**
 * Formats inline bold, italic, and code without dangerouslySetInnerHTML.
 */
function renderInlineFormatting(text, onEntityClick) {
  if (!text || typeof text !== 'string') return null;

  const boldParts = text.split(/(\*\*[^*]+\*\*)/g);
  return boldParts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const inner = part.slice(2, -2);
      return <strong key={i} className="font-semibold text-slate-100">{renderTextWithCitations(inner, onEntityClick)}</strong>;
    }
    const codeParts = part.split(/(`[^`]+`)/g);
    return codeParts.map((sub, j) => {
      if (sub.startsWith('`') && sub.endsWith('`')) {
        return (
          <code key={`${i}-${j}`} className="px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 text-xs font-mono border border-slate-700">
            {sub.slice(1, -1)}
          </code>
        );
      }
      return <Fragment key={`${i}-${j}`}>{renderTextWithCitations(sub, onEntityClick)}</Fragment>;
    });
  });
}

/**
 * Safely renders markdown string into clean React elements.
 * Prevents arbitrary HTML execution / XSS by never using dangerouslySetInnerHTML.
 */
export default function SafeMarkdown({ content, onEntityClick }) {
  if (!content || typeof content !== 'string') {
    return <p className="text-slate-500 text-sm italic">No content available.</p>;
  }

  const lines = content.split('\n');
  const elements = [];
  let inCodeBlock = false;
  let codeBlockLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs font-mono overflow-x-auto my-3">
            <code>{codeBlockLines.join('\n')}</code>
          </pre>
        );
        codeBlockLines = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-xl md:text-2xl font-bold text-slate-100 tracking-tight mt-6 mb-3 pb-2 border-b border-slate-800">
          {renderInlineFormatting(line.slice(2), onEntityClick)}
        </h1>
      );
    } else if (line.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-lg md:text-xl font-semibold text-slate-100 tracking-tight mt-5 mb-2.5">
          {renderInlineFormatting(line.slice(3), onEntityClick)}
        </h2>
      );
    } else if (line.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-sm md:text-base font-semibold text-slate-200 uppercase tracking-wide mt-4 mb-2 text-indigo-400">
          {renderInlineFormatting(line.slice(4), onEntityClick)}
        </h3>
      );
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <li key={`li-${i}`} className="ml-5 list-disc text-slate-300 text-sm leading-relaxed my-1">
          {renderInlineFormatting(line.slice(2), onEntityClick)}
        </li>
      );
    } else if (/^\d+\.\s/.test(line)) {
      const match = line.match(/^(\d+)\.\s(.*)$/);
      elements.push(
        <li key={`oli-${i}`} className="ml-5 list-decimal text-slate-300 text-sm leading-relaxed my-1">
          {renderInlineFormatting(match ? match[2] : line, onEntityClick)}
        </li>
      );
    } else if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={`quote-${i}`} className="border-l-2 border-indigo-500/60 pl-4 py-1 my-2 text-slate-300 text-sm italic bg-slate-900/40 rounded-r">
          {renderInlineFormatting(line.slice(2), onEntityClick)}
        </blockquote>
      );
    } else if (line.trim().length === 0) {
      elements.push(<div key={`space-${i}`} className="h-2" />);
    } else {
      elements.push(
        <p key={`p-${i}`} className="text-slate-300 text-sm leading-relaxed my-2">
          {renderInlineFormatting(line, onEntityClick)}
        </p>
      );
    }
  }

  if (inCodeBlock && codeBlockLines.length > 0) {
    elements.push(
      <pre key="code-unclosed" className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs font-mono overflow-x-auto my-3">
        <code>{codeBlockLines.join('\n')}</code>
      </pre>
    );
  }

  return <div className="space-y-1">{elements}</div>;
}
