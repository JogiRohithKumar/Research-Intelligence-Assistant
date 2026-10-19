/**
 * Validates and sanitizes external URLs to prevent javascript: or data: injection.
 * Only http:// and https:// URLs are allowed.
 */
export function sanitizeUrl(url) {
  if (!url || typeof url !== 'string') return null;
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  return null;
}

/**
 * Formats author list into standard scholarly citation style.
 */
export function formatAuthors(authors) {
  if (!authors || !Array.isArray(authors) || authors.length === 0) {
    return "Authors unavailable";
  }
  if (authors.length === 1) {
    return authors[0];
  }
  if (authors.length === 2) {
    return `${authors[0]} & ${authors[1]}`;
  }
  return `${authors[0]} et al. (${authors.length} authors)`;
}
