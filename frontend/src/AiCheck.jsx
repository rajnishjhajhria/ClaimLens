import { useEffect, useRef, useState } from "react";
import { host, langAttr, splitCitations, timeAgo } from "./factcheckUtils.js";
import { IconExternal, IconSearch } from "./Graphics.jsx";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const VERDICT_LABEL = {
  supported: "Sources support this claim",
  contradicted: "Sources contradict this claim",
  mixed: "Sources partly support this claim",
  unclear: "Sources don't settle this",
  not_a_claim: "This looks like an offer, not a claim",
};

const COMPANY_LABEL = {
  registered: "Sources show the company is registered",
  not_found: "No registration found in sources",
  unclear: "Sources don't settle this",
};

const COPY = {
  claim: {
    title: "Want a second opinion?",
    intro: (
      <>
        No published fact-check covers this claim. An AI can search the web and tell you what current sources say. This
        is <strong>not a fact-check</strong>, and the AI can be wrong.
      </>
    ),
    button: "Ask AI to check this",
    privacy: "The claim text is sent to Google Gemini and Google Search.",
    loading: "Searching the web and reading sources. This can take up to half a minute.",
    tag: "AI answer, not a fact-check",
  },
  company: {
    title: "Check the company",
    intro: (
      <>
        The message names a lender. An AI can search the web to see whether that company is registered with the RBI.
        This checks <strong>the company only, not whether this message is genuine</strong>, and the AI can be wrong.
      </>
    ),
    button: "Check the company",
    privacy: "The message text is sent to Google Gemini and Google Search.",
    loading: "Searching the web for this company and reading sources. This can take up to half a minute.",
    tag: "AI company check, not a fact-check",
  },
};

// Google's search suggestions are HTML from Google; show them in a sandbox so they cannot touch this page
function SearchSuggestions({ html }) {
  const doc = `<base target="_blank"><style>body{margin:0;font-family:system-ui,sans-serif}</style>${html}`;
  return (
    <iframe
      className="ai-suggest"
      title="Google Search suggestions"
      sandbox="allow-popups allow-popups-to-escape-sandbox"
      srcDoc={doc}
    />
  );
}

function Summary({ text, claimLang }) {
  return (
    <p className="ai-summary" lang={claimLang}>
      {splitCitations(text).map((p, i) =>
        p.cite ? (
          <sup key={i} className="ai-cite">
            <a href={`#ai-source-${p.cite}`}>{p.cite}</a>
          </sup>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
    </p>
  );
}

export default function AiCheck({ claim, message = "", kind = "claim", auto = false }) {
  const copy = COPY[kind] || COPY.claim;
  const labels = kind === "company" ? COMPANY_LABEL : VERDICT_LABEL;
  const [state, setState] = useState(auto ? "loading" : "idle"); // idle | loading | done | error
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const ctrl = useRef(null);

  useEffect(() => {
    if (auto) run(); // the company check starts by itself; the cache makes repeats free
    return () => ctrl.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run() {
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setState("loading");
    setError("");
    try {
      const res = await fetch(`${API}/ai-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim, message, kind }),
        signal: c.signal,
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "The AI check failed. Try again later.");
      setData(body);
      setState("done");
    } catch (e) {
      if (e.name === "AbortError") return;
      setError(e.message || "The AI check failed. Try again later.");
      setState("error");
    }
  }

  function cancel() {
    ctrl.current?.abort();
    setState("idle");
  }

  const claimLang = langAttr(/[਀-੿]/.test(claim) ? "pa" : /[ऀ-ॿ]/.test(claim) ? "hi" : "en");

  if (state === "idle" || state === "error") {
    return (
      <section className="ai ai-idle" aria-labelledby="ai-title">
        <div className="ai-head">
          <span className="ai-icon" aria-hidden="true">
            <IconSearch width={22} height={22} />
          </span>
          <div>
            <h3 id="ai-title">{copy.title}</h3>
            <p>{copy.intro}</p>
          </div>
        </div>
        {state === "error" && (
          <p className="ai-error" role="alert">
            {error}
          </p>
        )}
        <button type="button" className="ai-btn" onClick={run}>
          {copy.button}
        </button>
        <p className="ai-privacy">{copy.privacy}</p>
      </section>
    );
  }

  if (state === "loading") {
    return (
      <section className="ai ai-loading" aria-live="polite" aria-busy="true">
        <p>{copy.loading}</p>
        <button type="button" className="ai-link" onClick={cancel}>
          Cancel
        </button>
      </section>
    );
  }

  const verdict = data.verdict in labels ? data.verdict : "unclear";
  return (
    <section className={`ai ai-answer ai-v-${verdict}`} aria-labelledby="ai-title">
      <div className="ai-tag">{copy.tag}</div>
      <h3 id="ai-title">{labels[verdict]}</h3>
      <Summary text={data.summary} claimLang={claimLang} />

      {data.sources?.length > 0 && (
        <ol className="ai-sources">
          {data.sources.map((s) => (
            <li key={s.n} id={`ai-source-${s.n}`}>
              <a href={s.url} target="_blank" rel="noopener noreferrer">
                {s.title || host(s.url)}
                <IconExternal width={13} height={13} aria-hidden="true" />
              </a>
            </li>
          ))}
        </ol>
      )}

      {data.search_suggestions_html && <SearchSuggestions html={data.search_suggestions_html} />}

      <p className="ai-foot">
        AI can make mistakes. Check the sources before you share or act on this.
        {data.checked_at && ` Checked ${timeAgo(data.checked_at)}.`}
        {data.cached && " Shown from a recent check."}
      </p>
    </section>
  );
}
