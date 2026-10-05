import { useMemo, useState } from "react";
import {
  clip,
  dedupe,
  flattenQueries,
  formatDate,
  host,
  initials,
  langAttr,
  LANG_NAMES,
  overallVerdict,
  timeAgo,
  toneOf,
  verdictCounts,
  verdictOf,
} from "./factcheckUtils.js";
import AiCheck from "./AiCheck.jsx";
import { IconChevron, IconExternal, IconHelp, IconSearch, VerdictGauge, VerdictIcon } from "./Graphics.jsx";

function ResultRow({ r, unverified = false, related = false }) {
  const v0 = verdictOf(r, unverified);
  const rated = ["false", "misleading", "true"].includes(v0.key);
  // In "related" rows the rating belongs to a different claim, so show it neutrally and say so
  const v = related ? { key: "related", label: rated ? `Rated ${v0.label.toLowerCase()}` : v0.label } : v0;
  const fromSearch = r.source === "web search";
  const publisher = r.publisher || host(r.url);
  const date = formatDate(r.date);
  const lang = langAttr(r.language);
  return (
    <li className={`row row-${v.key}`}>
      <span className={`avatar ${toneOf(publisher)}`} aria-hidden="true">
        {initials(publisher)}
      </span>
      <div className="row-main">
        <div className="row-top">
          <span className="verdict">
            <VerdictIcon k={v0.key} width={14} height={14} strokeWidth={2.6} />
            {v.label}
          </span>
          <span className="publisher">{publisher}</span>
          {r.language && <span className="chip">{LANG_NAMES[r.language] || r.language}</span>}
          {date && (
            <time dateTime={r.date} title={timeAgo(r.date)}>
              {date}
            </time>
          )}
        </div>
        <a className="row-title" href={r.url} target="_blank" rel="noreferrer noopener" lang={lang}>
          {r.title || clip(r.claim, 120)}
        </a>
        {!fromSearch && r.claim && (
          <p className="row-claim" lang={lang}>
            {clip(r.claim, 200)}
          </p>
        )}
      </div>
      <IconExternal className="row-open" width={18} height={18} />
    </li>
  );
}

function summaryFor(result, view) {
  const shown = view.matches.length;
  switch (result.status) {
    case "no_claim":
      return {
        tone: "neutral",
        title: "No checkable claim found",
        body: "This message doesn't state something that can be fact-checked. If a claim is in there, paste just that sentence.",
      };
    case "unjudged":
      return {
        tone: "warn",
        title: "Possible fact-checks, not verified",
        body: "The AI checker is unavailable, so these are search matches. They may not be about your exact claim.",
      };
    case "match": {
      const total = result.matches_total ?? shown;
      const verdict = overallVerdict(verdictCounts(view.matches));
      const count = shown === 1 ? "1 fact-check" : `${shown} fact-checks`;
      const sub = `${verdict ? `${verdict.key === "mixed" ? "" : `${verdictCounts(view.matches)[verdict.key]} of ${verdictCounts(view.matches).rated} rated fact-checks say ${verdict.label.toLowerCase()}. `}` : ""}Based on ${count} of this claim or close variants. Check that the details match your message.`;
      return {
        tone: "match",
        verdict,
        title: verdict
          ? verdict.key === "mixed"
            ? "Fact-checkers disagree on this claim"
            : `Fact-checkers say this is likely ${verdict.label.toLowerCase()}`
          : shown === 1 ? "1 fact-check of this claim or a close variant" : `${shown} fact-checks of this claim or close variants`,
        body: (verdict ? sub + " " : "") + (total > shown ? `Showing the best ${shown} of ${total} matches.` : ""),
      };
    }
    default:
      return {
        tone: "neutral",
        title: "No fact-check of this exact claim yet",
        body:
          "Fact-checkers mostly review viral rumours, so everyday facts and fresh news often have none. That doesn't make the claim true or false." +
          (view.related.length ? " Related fact-checks are below." : ""),
      };
  }
}

function Facts({ items }) {
  const publishers = new Set(items.map((r) => r.publisher || host(r.url)).filter(Boolean));
  const langs = [...new Set(items.map((r) => r.language).filter(Boolean))];
  const newest = items
    .map((r) => new Date(r.date))
    .filter((d) => !isNaN(d))
    .sort((a, b) => b - a)[0];
  return (
    <dl className="facts">
      <div>
        <dt>Fact-checkers</dt>
        <dd>{publishers.size}</dd>
      </div>
      <div>
        <dt>Languages</dt>
        <dd>{langs.map((l) => LANG_NAMES[l] || l).join(", ") || "-"}</dd>
      </div>
      <div>
        <dt>Most recent</dt>
        <dd>{newest ? formatDate(newest) : "-"}</dd>
      </div>
    </dl>
  );
}

function Trace({ result, view }) {
  const ext = result.extraction || {};
  const queries = flattenQueries(ext.queries).slice(0, 8);
  const judged =
    result.status === "unjudged"
      ? "The AI checker was unavailable, so nothing was verified."
      : result.judged_by === "embedding"
        ? "Compared by text similarity, because the AI checker was unavailable."
        : "Each candidate was compared with your claim by an AI model.";
  return (
    <details className="trace">
      <summary>
        How we checked this
        <IconChevron className="chev" width={18} height={18} />
      </summary>
      <ol className="trace-steps">
        <li>
          <strong>Read your message.</strong>{" "}
          {ext.extracted_text ? "We read the text from your screenshot. " : ""}
          Language detected: {LANG_NAMES[ext.language] || ext.language || "unknown"}.
        </li>
        <li>
          <strong>Searched published fact-checks.</strong>
          {queries.length > 0 && (
            <span className="query-chips">
              {queries.map((q) => (
                <span className="chip" key={q} lang={/[\u0A00-\u0A7F]/.test(q) ? "pa" : /[\u0900-\u097F]/.test(q) ? "hi" : "en"}>
                  {q}
                </span>
              ))}
            </span>
          )}
        </li>
        <li>
          <strong>Compared {result.candidates_found ?? 0} candidates.</strong> {judged}
        </li>
        <li>
          <strong>Showed the closest.</strong> {result.matches_total ?? 0} matching, {view.related.length} related.
        </li>
      </ol>
    </details>
  );
}

export default function Results({ result }) {
  const [filter, setFilter] = useState("all");
  const view = useMemo(() => {
    const seen = [];
    return {
      matches: dedupe(result.matches, seen),
      related: dedupe(result.related, seen),
      unjudged: dedupe(result.unjudged, seen),
    };
  }, [result]);
  const counts = useMemo(() => verdictCounts(view.matches), [view.matches]);

  const summary = summaryFor(result, view);
  const claim = result.extraction?.claim;
  const readText = result.extraction?.extracted_text;
  const claimLang = langAttr(result.extraction?.language);
  const hasMatches = view.matches.length > 0;

  const filterOptions = [
    ["all", "All", view.matches.length],
    ["false", "False", counts.false],
    ["misleading", "Misleading", counts.misleading],
    ["true", "True", counts.true],
  ].filter(([k, , n]) => k === "all" || n > 0);
  const showFilters = hasMatches && filterOptions.length > 2;
  const shownMatches = filter === "all" ? view.matches : view.matches.filter((r) => verdictOf(r).key === filter);

  return (
    <div className="results">
      {readText && (
        <details className="read-text">
          <summary>Text read from the screenshot</summary>
          <p lang={claimLang}>{readText}</p>
        </details>
      )}

      {claim && (
        <figure className="claim">
          <figcaption>
            Claim we checked
            {result.extraction?.language && <span className="chip">{LANG_NAMES[result.extraction.language] || result.extraction.language}</span>}
          </figcaption>
          <blockquote lang={claimLang}>{claim}</blockquote>
        </figure>
      )}

      <section className={`summary summary-${summary.tone}`} aria-labelledby="summary-title">
        <div className="summary-visual">
          {result.status === "match" ? (
            <VerdictGauge counts={counts} />
          ) : result.status === "no_claim" ? (
            <span className="summary-icon">
              <IconHelp width={34} height={34} />
            </span>
          ) : (
            <span className="summary-icon">
              <IconSearch width={34} height={34} />
            </span>
          )}
        </div>
        <div className="summary-text">
          {summary.verdict && (
            <div className={`verdict-banner vb-${summary.verdict.key}`}>
              <VerdictIcon k={summary.verdict.key} width={22} height={22} aria-hidden="true" />
              <span>{summary.verdict.label.toUpperCase()}</span>
            </div>
          )}
          <h2 id="summary-title">{summary.title}</h2>
          {summary.body && <p>{summary.body}</p>}
          {result.judged_by === "embedding" && result.status === "match" && (
            <p className="reply-note">
              The AI checker was unavailable, so these matches are based on text similarity only and may be about a related claim.
            </p>
          )}
          {result.status === "match" && hasMatches && <Facts items={view.matches} />}
        </div>
      </section>

      {claim && (result.status === "no_match" || result.status === "unjudged") && (
        <AiCheck key={claim} claim={claim} />
      )}

      {showFilters && (
        <div className="filters" role="group" aria-label="Filter by rating">
          {filterOptions.map(([k, label, n]) => (
            <button
              type="button"
              key={k}
              className={`filter filter-${k}`}
              aria-pressed={filter === k}
              onClick={() => setFilter(k)}
            >
              {label}
              <span className="filter-n">{n}</span>
            </button>
          ))}
        </div>
      )}

      {hasMatches && (
        <ul className="rows">
          {shownMatches.map((r) => (
            <ResultRow key={r.url} r={r} />
          ))}
        </ul>
      )}

      {view.unjudged.length > 0 && (
        <ul className="rows">
          {view.unjudged.map((r) => (
            <ResultRow key={r.url} r={r} unverified />
          ))}
        </ul>
      )}

      {view.related.length > 0 && (
        <details className="related" open={!hasMatches}>
          <summary>
            Related fact-checks <span className="filter-n">{view.related.length}</span>
            <span className="related-note">Same topic, a different claim. Ratings are for those claims, not yours.</span>
            <IconChevron className="chev" width={18} height={18} />
          </summary>
          <ul className="rows">
            {view.related.map((r) => (
              <ResultRow key={r.url} r={r} related />
            ))}
          </ul>
        </details>
      )}

      {result.status !== "no_claim" && <Trace result={result} view={view} />}

      <p className="disclaimer">These are fact-checks published by other organisations. This tool doesn't decide what is true.</p>
    </div>
  );
}
