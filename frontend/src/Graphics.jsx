const base = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
  focusable: "false",
};

export const IconX = (p) => (
  <svg {...base} {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);
export const IconAlert = (p) => (
  <svg {...base} {...p}>
    <path d="M12 9v4M12 17h.01" />
    <path d="M10.3 3.9L2.6 17.3A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.7L13.7 3.9a2 2 0 0 0-3.4 0z" />
  </svg>
);
export const IconCheck = (p) => (
  <svg {...base} {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </svg>
);
export const IconHelp = (p) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.6 9.6a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1.1.9-1.1 1.7M12 17h.01" />
  </svg>
);
export const IconExternal = (p) => (
  <svg {...base} {...p}>
    <path d="M14 4h6v6M20 4l-9 9M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5" />
  </svg>
);
export const IconImage = (p) => (
  <svg {...base} {...p}>
    <rect x="3" y="4" width="18" height="16" rx="3" />
    <circle cx="9" cy="10" r="1.6" />
    <path d="M21 16l-5-5-8 8" />
  </svg>
);
export const IconText = (p) => (
  <svg {...base} {...p}>
    <path d="M5 6h14M5 12h14M5 18h9" />
  </svg>
);
export const IconUpload = (p) => (
  <svg {...base} {...p}>
    <path d="M12 16V5M7.5 9.5L12 5l4.5 4.5M5 19h14" />
  </svg>
);
export const IconSearch = (p) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M16 16l4.5 4.5" />
  </svg>
);
export const IconChevron = (p) => (
  <svg {...base} {...p}>
    <path d="M7 10l5 5 5-5" />
  </svg>
);

export function VerdictIcon({ k, ...p }) {
  if (k === "false") return <IconX {...p} />;
  if (k === "misleading") return <IconAlert {...p} />;
  if (k === "true") return <IconCheck {...p} />;
  return <IconHelp {...p} />;
}

export function Logo({ size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 34 34" aria-hidden="true" focusable="false">
      <rect width="34" height="34" rx="10" fill="#fff" />
      <path d="M9 18.5l5.2 5.2L25 11" fill="none" stroke="#2E3396" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// A forward spreading through a network and arriving at a checked message.
// Three light pulses travel once on load and stop on the check mark.
export function HeroArt({ className }) {
  const nodes = [
    [36, 168, 5],
    [92, 78, 7],
    [118, 246, 6],
    [196, 132, 9],
    [210, 286, 7],
    [262, 44, 6],
    [418, 64, 7],
    [448, 262, 8],
    [330, 320, 5],
    [470, 150, 5],
  ];
  const edges = [
    "M36 168 Q56 96 92 78",
    "M92 78 Q150 90 196 132",
    "M118 246 Q150 200 196 132",
    "M196 132 Q262 120 338 176",
    "M210 286 Q270 250 338 176",
    "M262 44 Q300 100 338 176",
    "M418 64 Q390 120 338 176",
    "M448 262 Q400 230 338 176",
    "M92 78 Q170 40 262 44",
    "M118 246 Q160 286 210 286",
    "M210 286 Q270 330 330 320",
    "M418 64 Q470 90 470 150",
  ];
  const pulses = [
    { d: "M36 168 Q56 96 92 78 Q150 90 196 132 Q262 120 338 176", begin: "0.5s" },
    { d: "M118 246 Q150 200 196 132 Q262 120 338 176", begin: "1.1s" },
    { d: "M448 262 Q400 230 338 176", begin: "1.7s" },
  ];
  return (
    <svg className={className} viewBox="0 0 500 350" role="img" aria-label="A forwarded message spreading through a network and reaching a checked message">
      <g fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="1.6" strokeLinecap="round">
        {edges.map((d) => (
          <path key={d} d={d} />
        ))}
      </g>
      <g fill="rgba(255,255,255,0.88)">
        {nodes.map(([x, y, r]) => (
          <circle key={`${x}-${y}`} cx={x} cy={y} r={r} />
        ))}
      </g>
      {pulses.map((p) => (
        <circle key={p.d} className="pulse" r="5" fill="#B9BEFF" opacity="0">
          <animate attributeName="opacity" from="0" to="1" dur="0.01s" begin={p.begin} fill="freeze" />
          <animateMotion dur="2.2s" begin={p.begin} fill="freeze" path={p.d} calcMode="spline" keySplines="0.3 0.1 0.2 1" keyTimes="0;1" />
        </circle>
      ))}
      <circle cx="338" cy="176" r="46" fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5" />
      <circle cx="338" cy="176" r="31" fill="#fff" />
      <path d="M324 177l9 9 17-19" fill="none" stroke="#2E3396" strokeWidth="5.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const ARC = "M20 112 A90 90 0 0 1 200 112";
const LABELS = { false: "rated false", misleading: "rated misleading", true: "rated true" };

// Semicircle showing how professional fact-checkers rated the matches.
export function VerdictGauge({ counts }) {
  const order = ["false", "misleading", "true"];
  const segs = order.filter((k) => counts[k] > 0);
  let start = 0;
  const arcs = segs.map((k) => {
    const len = (counts[k] / counts.rated) * 100;
    const el = (
      <path
        key={k}
        d={ARC}
        pathLength="100"
        className={`gauge-seg gauge-${k}`}
        style={{ strokeDasharray: `${segs.length > 1 ? Math.max(len - 1.5, 0.1) : len} 100`, strokeDashoffset: -start }}
      />
    );
    start += len;
    return el;
  });
  const top = order.reduce((a, b) => (counts[b] > counts[a] ? b : a), "false");
  const label = counts.rated
    ? `${counts[top]} of ${counts.rated} fact-checks ${LABELS[top]}`
    : "No ratings to show";
  return (
    <div className="gauge" role="img" aria-label={label}>
      <svg viewBox="0 0 220 128" aria-hidden="true">
        <path d={ARC} pathLength="100" className="gauge-track" />
        {arcs}
      </svg>
      <div className="gauge-read" aria-hidden="true">
        {counts.rated ? (
          <>
            <span className="gauge-num">
              {counts[top]}
              <span className="gauge-of"> of {counts.rated}</span>
            </span>
            <span className="gauge-label">{LABELS[top]}</span>
          </>
        ) : (
          <span className="gauge-label">No ratings</span>
        )}
      </div>
    </div>
  );
}
