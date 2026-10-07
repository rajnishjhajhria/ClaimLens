// Recent checks, kept only in this browser (localStorage). Every call is wrapped: storage can be blocked or full.
const KEY = "claimlens.history.v1";
const MAX_ITEMS = 12;

export function loadHistory() {
  try {
    const items = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(items) ? items.filter((i) => i && i.id && i.result && i.claim) : [];
  } catch {
    return [];
  }
}

function store(items) {
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    /* storage unavailable: history simply does not persist */
  }
}

// Offers and account alerts are never saved, and the original message text is stripped
// from everything that is, so a pasted loan alert or screenshot text does not stay on the device.
export function saveToHistory(result, via) {
  const claim = result?.extraction?.claim;
  if (!claim || result.status === "notice" || result.status === "no_claim") return loadHistory();
  const { source_text, extracted_text, ...extraction } = result.extraction;
  const item = {
    id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
    t: new Date().toISOString(),
    via,
    claim,
    result: { ...result, extraction },
  };
  const rest = loadHistory().filter((i) => i.claim.toLowerCase() !== claim.toLowerCase());
  const next = [item, ...rest].slice(0, MAX_ITEMS);
  store(next);
  return next;
}

export function clearHistory() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  return [];
}
