export const LANG_NAMES = { en: "English", hi: "हिन्दी", pa: "ਪੰਜਾਬੀ", hinglish: "Hinglish" };

// HTML lang attribute so the browser picks the right font for Hindi and Punjabi text
export function langAttr(code) {
  if (!code) return undefined;
  return code === "hinglish" ? "en" : code;
}

const MISLEADING_RE =
  /(misleading|partly|partially|missing context|unproven|exaggerat|half.?true|भ्रामक|आंशिक|ਗੁੰਮਰਾਹ)/i;
const FALSE_RE =
  /(pants on fire|false|fake|incorrect|not true|baseless|fabricat|hoax|scam|no evidence|फर्ज़ी|फर्जी|झूठ|गलत|फेक|ਝੂਠ|ਫਰਜ਼ੀ|ਗਲਤ)/i;
const TRUE_RE = /^\s*(mostly true|true|correct|accurate|सही|सच|ਸੱਚ)/i;

// key drives colour and icon; label is the words shown to the person
export function verdictOf(r, unverified = false) {
  if (unverified) return { key: "unverified", label: "Unverified match" };
  if (r.source === "web search") return { key: "article", label: "Fact-check article" };
  const t = r.rating || "";
  if (MISLEADING_RE.test(t)) return { key: "misleading", label: "Misleading" };
  if (FALSE_RE.test(t)) return { key: "false", label: "False" };
  if (TRUE_RE.test(t)) return { key: "true", label: "True" };
  return { key: "article", label: t && t.length <= 24 ? t : "Not rated" };
}

export function host(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

const STOP = new Set(["fact", "check", "factcheck", "the", "a", "an", "of", "in", "to", "is", "did", "does"]);

function tokens(title) {
  const words = (title || "").toLowerCase().match(/[\p{L}\p{M}\p{N}]+/gu) || [];
  return new Set(
    words
      .map((w) => (w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w))
      .filter((w) => !STOP.has(w))
  );
}

function jaccard(a, b) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  return inter / (a.size + b.size - inter);
}

// Drops the same story shown twice under different URLs (same site, near-identical title).
// `seen` is shared across lists so a "related" item can't repeat a "match".
export function dedupe(items, seen, threshold = 0.75) {
  const out = [];
  for (const r of items || []) {
    const h = host(r.url);
    const t = tokens(r.title || r.claim);
    const dup = seen.some((s) => s.host === h && jaccard(s.tokens, t) >= threshold);
    if (!dup) {
      out.push(r);
      seen.push({ host: h, tokens: t });
    }
  }
  return out;
}

// counts of rated verdicts among items (used by the gauge and the summary)
export function verdictCounts(items) {
  const c = { false: 0, misleading: 0, true: 0, other: 0 };
  for (const r of items || []) {
    const k = verdictOf(r).key;
    if (k in c) c[k]++;
    else c.other++;
  }
  c.rated = c.false + c.misleading + c.true;
  c.total = c.rated + c.other;
  return c;
}

export function formatDate(d) {
  if (!d) return "";
  const date = new Date(d);
  return isNaN(date) ? "" : date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
}

export function timeAgo(d) {
  const t = new Date(d);
  if (!d || isNaN(t)) return "";
  const days = Math.round((Date.now() - t.getTime()) / 86400000);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (days < 1) return "today";
  if (days < 30) return rtf.format(-days, "day");
  if (days < 365) return rtf.format(-Math.round(days / 30), "month");
  return rtf.format(-Math.round(days / 365), "year");
}

export function clip(text, n) {
  if (!text) return "";
  return text.length > n ? text.slice(0, n).trimEnd() + "…" : text;
}

// two-letter monogram for a publisher avatar
export function initials(name) {
  const words = (name || "")
    .replace(/[^\p{L}\p{M}\p{N}\s]/gu, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!words.length) return "?";
  const first = Array.from(words[0])[0];
  const second = words[1] ? Array.from(words[1])[0] : "";
  return (first + second).toUpperCase();
}

const TONES = ["tone-a", "tone-b", "tone-c", "tone-d", "tone-e", "tone-f"];
export function toneOf(name) {
  let h = 0;
  for (const ch of name || "") h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return TONES[h % TONES.length];
}

// the short search queries the backend used, de-duplicated, for the "how we checked" trace
export function flattenQueries(queries) {
  const out = [];
  for (const lang of ["en", "hi", "pa"]) {
    for (const q of queries?.[lang] || []) {
      if (q && !out.includes(q)) out.push(q);
    }
  }
  return out;
}

// split an AI summary like "Text.[[1]][[2]] More" into plain text and citation numbers for <sup> links
export function splitCitations(text) {
  const parts = [];
  const re = /\[\[(\d+)\]\]/g;
  let last = 0;
  let m;
  while ((m = re.exec(text || "")) !== null) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) });
    parts.push({ cite: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < (text || "").length) parts.push({ text: text.slice(last) });
  return parts;
}

// One overall word for a set of matched fact-checks, or null when none carries a clear rating
export function overallVerdict(counts) {
  if (!counts.rated) return null;
  const top = ["false", "misleading", "true"].reduce((a, b) => (counts[b] > counts[a] ? b : a), "false");
  if (counts[top] / counts.rated < 0.7) return { key: "mixed", label: "Mixed ratings" };
  return { key: top, label: { false: "False", misleading: "Misleading", true: "True" }[top] };
}
