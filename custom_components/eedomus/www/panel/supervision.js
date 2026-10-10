/**
 * Supervision tab of the Eedomus config panel (CAP-9 + CAP-5 view).
 *
 * Real ES module imported by www/eedomus-panel.js: the tab's
 * stylesheet chunk and the supervision prototype mixin. Two parallel
 * loads per tab visit (eedomus/get_box_metrics +
 * eedomus/get_backfill_state) with independent state slots — same
 * loading contract as the other lazy tabs: no subscription, no
 * polling. Every action issues its CAP-5 verb and re-renders from the
 * response's {state} — never a second get_backfill_state round trip.
 *
 * Charts are inline SVG themed through HA CSS variables only — no HA
 * chart component is exposed to the panel context (esbuild internals,
 * version-hashed URLs) and no chart library may be vendored for this
 * (toolchain-free vanilla). Every metric value carries its textual
 * equivalent next to the chart: the chart is never the sole carrier
 * of the information (svg aria-hidden, values readable as text).
 * The queue rows are the same discipline: statuses are text (never
 * color alone), each action gives a nominative aria-live feedback,
 * and Ignore follows the two-gesture confirmation (pointer and
 * keyboard) of the historique restore pattern.
 */

import {
  BACKFILL_PROGRESS_STYLES,
  backfillProgressHtml,
  escapeHtml,
  truncateDetailText,
} from './shared.js';

export const SUPERVISION_STYLES = `
        .supervision-section { margin: 0 0 24px; }
        .supervision-section h2 {
          font-size: 15px; font-weight: 500; margin: 0 0 8px;
        }
        .metric-grid {
          display: grid; gap: 12px;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        }
        .metric-card {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 14px 16px;
        }
        .metric-card h3 {
          font-size: 13px; font-weight: 500; margin: 0 0 8px;
          color: var(--secondary-text-color);
        }
        .metric-value { font-size: 20px; font-weight: 400; margin: 0 0 4px; }
        .metric-text {
          color: var(--secondary-text-color); font-size: 13px; margin: 0;
        }
        .metric-chart {
          display: block; width: 100%; height: 120px; margin-top: 10px;
        }
        .metric-gauge { height: 96px; }
        .metric-chips {
          display: flex; flex-wrap: wrap; gap: 4px; margin: 10px 0 0;
        }
        .metric-chip {
          display: inline-flex; align-items: center;
          padding: 2px 8px;
          border-radius: var(--ha-chip-border-radius, 16px);
          font-size: 12px;
          color: var(--primary-text-color);
          background: color-mix(
            in srgb, var(--primary-color) 12%, var(--card-background-color)
          );
        }
        .metric-skeleton {
          height: 180px;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          opacity: 0.6;
        }
        .supervision-link { margin: 4px 0 12px; }
        .backfill-section { margin: 32px 0 0; }
        .backfill-section h2 {
          font-size: 15px; font-weight: 500; margin: 0 0 8px;
        }
        .backfill-section h3 {
          font-size: 14px; font-weight: 500; margin: 16px 0 4px;
        }
        .backfill-switch {
          display: inline-flex; align-items: center; gap: 8px;
          font: inherit; min-height: 44px; padding: 8px 16px;
          cursor: pointer; color: var(--primary-text-color);
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 9999px;
          margin: 0 0 8px;
        }
        .backfill-switch[aria-checked="true"] {
          border-color: var(--primary-color); font-weight: 500;
        }
        .backfill-switch-state { color: var(--secondary-text-color); }
        .backfill-switch:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
        .backfill-rows { margin-top: 4px; }
        .backfill-row {
          display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
          padding: 10px 0; border-bottom: 1px solid var(--divider-color);
        }
        .backfill-row:last-child { border-bottom: none; }
        .backfill-name { font-weight: 500; }
        .backfill-periph, .backfill-position, .backfill-error-detail {
          color: var(--secondary-text-color); font-size: 13px;
        }
        .backfill-status {
          font-size: 13px; color: var(--secondary-text-color);
        }
        .backfill-actions {
          display: flex; flex-wrap: wrap; gap: 8px; margin-left: auto;
        }
        .backfill-alert {
          width: 100%; margin: 0 0 4px; font-size: 13px;
          color: var(--primary-text-color);
        }
        ${BACKFILL_PROGRESS_STYLES}
        .backfill-progress { width: 100%; margin: 0 0 4px; }
        .backfill-skeleton-row {
          height: 44px; margin-bottom: 8px;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          opacity: 0.6;
        }
`;

// Chart canvas: fixed viewBox scaled by CSS width — the points are
// computed in this coordinate space, the theme stays in CSS variables.
const CHART_WIDTH = 300;
const CHART_HEIGHT = 120;
const CHART_PAD = 6;

// Numeric coercion of a series value: a missing or non-finite entry
// draws as 0 instead of poisoning the min/max scaling with NaN.
function supervisionSeriesNumbers(values) {
  if (!Array.isArray(values)) {
    return [];
  }
  return values.map((value) =>
    typeof value === 'number' && Number.isFinite(value) ? value : 0
  );
}

// Series extraction from the cycle records: only finite numbers join
// the series — a data gap is skipped, never coerced to a fake dip to
// zero. An emptied series renders no chart (the textual equivalent
// still carries the information).
function supervisionCycleSeries(cycles, key) {
  const values = [];
  for (const cycle of cycles) {
    const value = cycle ? cycle[key] : null;
    if (typeof value === 'number' && Number.isFinite(value)) {
      values.push(value);
    }
  }
  return values;
}

// Line-chart points of a series, in the chart coordinate space.
// A flat series draws as a mid-height line (min forced below max),
// never a zero-height sliver clipped to the padding edge.
export function supervisionChartPoints(
  values,
  width = CHART_WIDTH,
  height = CHART_HEIGHT,
  pad = CHART_PAD
) {
  const numbers = supervisionSeriesNumbers(values);
  if (numbers.length === 0) {
    return [];
  }
  let min = Math.min(...numbers);
  const max = Math.max(...numbers);
  if (min === max) {
    min = max - 1;
  }
  const span = max - min;
  const innerWidth = width - 2 * pad;
  const innerHeight = height - 2 * pad;
  return numbers.map((value, index) => {
    const x = numbers.length === 1
      ? pad + innerWidth / 2
      : pad + (innerWidth * index) / (numbers.length - 1);
    const y = pad + innerHeight - ((value - min) / span) * innerHeight;
    return [Math.round(x * 10) / 10, Math.round(y * 10) / 10];
  });
}

// SVG path data of a line chart ('M x,y L x,y …'), '' when empty.
export function supervisionLinePath(points) {
  if (!Array.isArray(points) || points.length === 0) {
    return '';
  }
  return points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${point[0]},${point[1]}`)
    .join(' ');
}

// Bar-chart rectangles of a series, scaled against a zero baseline so
// bar heights compare real magnitudes (unlike the line chart's
// min-max window). A non-zero value never vanishes to a zero-height
// sliver: it keeps a 2px floor.
export function supervisionBarRects(
  values,
  width = CHART_WIDTH,
  height = CHART_HEIGHT,
  pad = CHART_PAD
) {
  const numbers = supervisionSeriesNumbers(values);
  if (numbers.length === 0) {
    return [];
  }
  const max = Math.max(...numbers, 0);
  const innerWidth = width - 2 * pad;
  const innerHeight = height - 2 * pad;
  const slot = innerWidth / numbers.length;
  const barWidth = Math.max(Math.min(slot - 2, 12), 2);
  return numbers.map((value, index) => {
    const scale = max > 0 ? value / max : 0;
    const barHeight = Math.max(scale * innerHeight, value > 0 ? 2 : 0);
    return {
      x: Math.round((pad + slot * index + (slot - barWidth) / 2) * 10) / 10,
      y: Math.round((pad + innerHeight - barHeight) * 10) / 10,
      width: Math.round(barWidth * 10) / 10,
      height: Math.round(barHeight * 10) / 10,
    };
  });
}

// Seconds formatting of a metric value: three decimals, the unit
// suffix only when asked (the textual equivalents already carry it in
// their templates); a missing value renders the em dash.
export function supervisionFormatSeconds(value, withUnit) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '—';
  }
  const text = value.toFixed(3);
  return withUnit ? `${text} s` : text;
}

// Integer formatting of a count metric; missing value → em dash.
export function supervisionFormatCount(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '—';
  }
  return String(Math.round(value));
}

// One-decimal formatting of a metric value (CPU %, free space kB);
// missing value → em dash.
export function supervisionFormatDecimal(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '—';
  }
  return value.toFixed(1);
}

// Display formatting of a retry_after timestamp: the ISO local text
// served by _json_safe ("2026-10-07T21:04:00+02:00") becomes readable
// "07/10 21:04" (day/month + HH:MM, the offset dropped for display) —
// the full ISO stays in the title. Unparseable text passes through
// honestly, a missing value renders the em dash.
export function supervisionFormatTimestamp(value) {
  const text = String(value || '');
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(text);
  if (!match) {
    return text || '—';
  }
  return `${match[3]}/${match[2]} ${match[4]}:${match[5]}`;
}

// The five CAP-5 status tokens (4.1 contract): every one maps to a
// catalog label; an unknown token keeps a neutral text carrying the
// raw value — never dropped, never empty (same contract as the
// coherence chips).
const BACKFILL_STATUS_KEYS = {
  priority: 'panel.supervision.backfill.status.priority',
  in_progress: 'panel.supervision.backfill.status.in_progress',
  error: 'panel.supervision.backfill.status.error',
  paused: 'panel.supervision.backfill.status.paused',
  pending: 'panel.supervision.backfill.status.pending',
};

export function supervisionBackfillStatusText(status, t) {
  const key = BACKFILL_STATUS_KEYS[status];
  if (key) {
    return t(key);
  }
  return t('panel.supervision.backfill.status.unknown', {
    raw: String(status || '—'),
  });
}

// One websocket verb per row action (4.1, frozen backend contract).
// entry_id stays out of the payloads: mono-box resolution like
// get_peripherals, the backend owns the fan-out.
const BACKFILL_COMMANDS = {
  retry: { type: 'eedomus/backfill_retry_now' },
  prioritize: { type: 'eedomus/backfill_prioritize' },
  pause: { type: 'eedomus/backfill_set_paused', paused: true },
  resume: { type: 'eedomus/backfill_set_paused', paused: false },
  ignore: { type: 'eedomus/backfill_set_ignored', ignored: true },
  reactivate: { type: 'eedomus/backfill_set_ignored', ignored: false },
};

// Nominative feedback per successful action (aria-live).
const BACKFILL_FEEDBACK_KEYS = {
  retry: 'panel.supervision.backfill.feedback.retry',
  prioritize: 'panel.supervision.backfill.feedback.prioritize',
  pause: 'panel.supervision.backfill.feedback.pause',
  resume: 'panel.supervision.backfill.feedback.resume',
  ignore: 'panel.supervision.backfill.feedback.ignore',
  reactivate: 'panel.supervision.backfill.feedback.reactivate',
};

// Post-action focus target per verb: pause hands over to the resume
// control (and vice versa), an ignored line to its Reactivate entry,
// and a reactivated line to the queue row's retry control (the row
// re-enters the queue and retry is its leading action) — the
// re-rendered counterpart keeps the keyboard on the line.
const BACKFILL_FOCUS_ACTION = {
  retry: 'retry',
  prioritize: 'prioritize',
  pause: 'resume',
  resume: 'pause',
  ignore: 'reactivate',
  reactivate: 'retry',
};

// Inline themed line chart. The svg is aria-hidden: the textual
// equivalent next to it carries the information, the chart never
// duplicates it into an accessible name.
export function supervisionLineChartHtml(values) {
  const path = supervisionLinePath(supervisionChartPoints(values));
  if (!path) {
    return '';
  }
  return `<svg class="metric-chart" viewBox="0 0 ${CHART_WIDTH} ${CHART_HEIGHT}" aria-hidden="true" focusable="false"><path d="${path}" fill="none" stroke="var(--primary-color)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"></path></svg>`;
}

// Inline themed bar chart (same accessibility contract as the line).
export function supervisionBarChartHtml(values) {
  const rects = supervisionBarRects(values);
  if (rects.length === 0) {
    return '';
  }
  const bars = rects
    .map((rect) => `<rect x="${rect.x}" y="${rect.y}" width="${rect.width}" height="${rect.height}" fill="var(--primary-color)" opacity="0.55"></rect>`)
    .join('');
  return `<svg class="metric-chart" viewBox="0 0 ${CHART_WIDTH} ${CHART_HEIGHT}" aria-hidden="true" focusable="false">${bars}</svg>`;
}

// One metric chart card: label, current value as text, textual
// equivalent of the series, then the chart. Pure — the translator is
// injected so a mid-session locale switch never replays stale text,
// and every interpolation is escaped at the boundary (the helper is
// exported: a value or a text is never trusted as markup).
export function supervisionMetricCardHtml(card, t) {
  const chart = card.kind === 'bars'
    ? supervisionBarChartHtml(card.series)
    : supervisionLineChartHtml(card.series);
  return `
    <div class="metric-card">
      <h3>${escapeHtml(t(card.titleKey))}</h3>
      <p class="metric-value">${escapeHtml(card.value)}</p>
      <p class="metric-text">${escapeHtml(t(card.textKey, card.textParams || {}))}</p>
      ${chart}
    </div>
  `;
}

// SVG path of a semicircular gauge arc (CAP-9 activity card): the
// fraction clamps to [0, 1]; 0 draws no arc, 1 spans the full
// semicircle. Pure — the arcs of the tests are exact strings.
export function supervisionGaugeArc(fraction, radius = 40) {
  const value = Number(fraction);
  if (!Number.isFinite(value) || value <= 0) {
    return '';
  }
  const clamped = Math.min(value, 1);
  if (clamped >= 1) {
    return `M ${50 - radius} 50 A ${radius} ${radius} 0 0 1 ${50 + radius} 50`;
  }
  const theta = Math.PI * (1 - clamped);
  const x = 50 + radius * Math.cos(theta);
  const y = 50 - radius * Math.sin(theta);
  return (
    `M ${50 - radius} 50 A ${radius} ${radius} 0 0 1 ` +
    `${x.toFixed(1)} ${y.toFixed(1)}`
  );
}

// Inline themed gauge (same accessibility contract as the charts: the
// svg is aria-hidden, the textual equivalent beside it carries the
// information — never the arc color alone).
export function supervisionGaugeHtml(fraction) {
  const arc = supervisionGaugeArc(fraction);
  const track = `M 10 50 A 40 40 0 0 1 90 50`;
  const valuePath = arc
    ? `<path d="${arc}" fill="none" stroke="var(--primary-color)" ` +
      'stroke-width="8" stroke-linecap="round"></path>'
    : '';
  return (
    `<svg class="metric-chart metric-gauge" viewBox="0 0 100 56" ` +
    'aria-hidden="true" focusable="false">' +
    `<path d="${track}" fill="none" stroke="var(--divider-color)" ` +
    `stroke-width="8" stroke-linecap="round"></path>${valuePath}</svg>`
  );
}

// Category chips of the periph count card: one chip per mapped entity
// type, sorted by count, name and count escaped at the boundary —
// the coherence-chip discipline (text on a 12% tint, never the color
// alone).
export function supervisionCategoryChipsHtml(categories) {
  if (!categories || typeof categories !== 'object') {
    return '';
  }
  const entries = Object.entries(categories)
    .filter(([, count]) => typeof count === 'number' && count > 0)
    .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
  if (entries.length === 0) {
    return '';
  }
  const chips = entries
    .map(
      ([name, count]) =>
        `<span class="metric-chip">${escapeHtml(name)} ` +
        `${escapeHtml(String(count))}</span>`
    )
    .join('');
  return `<p class="metric-chips">${chips}</p>`;
}

// One metric value card (no chart): label, current value, textual
// equivalent, then the optional gauge and chips. Same escaping
// contract as the chart card.
export function supervisionValueCardHtml(card, t) {
  const gauge = card.kind === 'gauge'
    ? supervisionGaugeHtml(card.fraction)
    : '';
  const chips = card.chips || '';
  return `
    <div class="metric-card">
      <h3>${escapeHtml(t(card.titleKey))}</h3>
      <p class="metric-value">${escapeHtml(card.value)}</p>
      <p class="metric-text">${escapeHtml(t(card.textKey, card.textParams || {}))}</p>
      ${gauge}
      ${chips}
    </div>
  `;
}

export function applySupervisionMixin(EedomusConfigPanel) {
  Object.assign(EedomusConfigPanel.prototype, {
  // ================= Supervision (CAP-9) =================

  async _loadMetrics() {
    // In-flight guard + generation (mirror of _loadCoherence): a
    // hass reassignment during the await neither duplicates the ws
    // call nor lets a superseded resolution write stale metrics.
    if (!this._hass || this._metricsLoading) {
      return;
    }
    this._metricsLoading = true;
    this._metricsError = null;
    this._metricsErrorDetail = null;
    this._metrics = null;
    const generation = ++this._metricsGeneration;
    if (this._tab === 'supervision') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        // Retry shows the skeleton again, never a stale error.
        content.innerHTML = this._renderSupervisionTab();
      }
    }
    let result = null;
    try {
      result = await this._hass.callWS({
        type: 'eedomus/get_box_metrics',
      });
    } catch (err) {
      result = null;
      if (generation === this._metricsGeneration) {
        // The raw backend detail (message, else error code) is stored
        // apart: it renders escaped as-is, never through t() — FR
        // users would otherwise read untranslated text, and a raw
        // message shaped like "{token}" would go through token
        // replacement. The catalog-key path stays for the generic
        // refusal case.
        this._metricsErrorDetail = (err && (err.message || err.code)) ||
          null;
        this._metricsError = 'panel.common.command_refused';
      }
    }
    this._metricsLoading = false;
    if (generation !== this._metricsGeneration) {
      // A newer load superseded this one: its data is stale, dropped.
      return;
    }
    // A falsy answer renders the positive empty state, never an
    // eternal skeleton (same coercion as the coherence load).
    this._metrics = result || { boxes: [] };
    if (this._tab === 'supervision') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        content.innerHTML = this._renderSupervisionTab();
      }
    }
  },

  _renderSupervisionTab() {
    // Single composition point (EXPERIENCE l.31): the box sections,
    // then the coherence link, then the backfill queue. The two data
    // zones carry independent state slots — one failing never blanks
    // the other (EXPERIENCE l.94).
    return `
      ${this._renderMetricsZone()}
      <p class="supervision-link">
        <button class="row-action" type="button" data-goto-coherence="1">
          ${this.t('panel.supervision.link.coherence')}
        </button>
      </p>
      ${this._renderBackfillZone()}
    `;
  },

  _renderMetricsZone() {
    if (this._metricsError) {
      // The raw backend detail is rendered escaped as-is (never
      // re-translated); the generic refusal keeps its catalog-key
      // path through t().
      const detail = this._metricsErrorDetail
        ? this._escapeHtml(this._metricsErrorDetail)
        : this._escapeHtml(this.t(this._metricsError));
      return `
        <div class="state-message" role="alert">
          ${this.t('panel.supervision.error.load', { err: detail })}
          <br>
          <button class="retry" type="button" data-retry="metrics">
            ${this.t('panel.common.retry')}
          </button>
        </div>
      `;
    }
    if (this._metrics === null) {
      return this._renderSupervisionSkeleton();
    }
    const boxes = (this._metrics && this._metrics.boxes) || [];
    if (boxes.length === 0) {
      return `
        <div class="state-message">
          ${this.t('panel.supervision.empty')}
        </div>
      `;
    }
    return boxes
      .map((box, index) => this._renderSupervisionBox(box, index))
      .join('');
  },

  _renderSupervisionSkeleton() {
    // Skeleton shaped like the expected content: chart cards. inert
    // keeps the placeholders out of the tab order; the wrapper status
    // announces the loading state to screen readers.
    const card = '<div class="metric-skeleton" aria-hidden="true"></div>';
    return `
      <div role="status" aria-label="${this._escapeHtml(
        this.t('panel.supervision.skeleton.aria')
      )}">
        <div class="metric-grid" aria-hidden="true" inert>
          ${card.repeat(3)}
        </div>
      </div>
    `;
  },

  _renderSupervisionBox(box, index) {
    const cycles = (box && box.cycles) || [];
    const rawName = box && (box.name || box.entry_id);
    const title = rawName
      ? this.t('panel.supervision.box.title', {
          name: this._escapeHtml(String(rawName)),
        })
      : this.t('panel.supervision.box.fallback', { n: index + 1 });
    if (cycles.length === 0) {
      // Positive empty state: nothing is wrong, the buffer simply has
      // no cycle yet (fresh boot or first refresh still running).
      return `
        <section class="supervision-section">
          <h2>${title}</h2>
          <div class="state-message">
            ${this.t('panel.supervision.empty')}
          </div>
        </section>
      `;
    }
    const last = cycles[cycles.length - 1];
    const refreshSeries = supervisionCycleSeries(cycles, 'refresh_time');
    const cpuSeries = supervisionCycleSeries(cycles, 'cpu');
    const freeSeries = supervisionCycleSeries(cycles, 'free_space_kb');
    const categories =
      box && typeof box.periphs_by_category === 'object'
        ? box.periphs_by_category
        : null;
    const activeRaw = box ? box.active_periphs_last_hour : null;
    const active =
      typeof activeRaw === 'number' && Number.isFinite(activeRaw)
        ? activeRaw
        : null;
    const categoryTotal = categories
      ? Object.values(categories).reduce(
          (sum, count) => (typeof count === 'number' ? sum + count : sum),
          0
        )
        : null;
    // Each card: label + current value + textual equivalent (+ chart
    // or gauge + chips). The equivalent names the numbers — the visual
    // is never the only carrier (Accessibility floor). Card set per
    // the spine (2026-10-08): refresh chart, activity gauge, static
    // count with category chips, system chart. The system card hides
    // when no CPU sample exists — never a half-empty card.
    const lastFinite = (series) =>
      series.length > 0 ? series[series.length - 1] : null;
    const cards = [
      supervisionMetricCardHtml(
        {
          titleKey: 'panel.supervision.card.refresh_time',
          kind: 'line',
          series: refreshSeries,
          value: supervisionFormatSeconds(last.refresh_time, true),
          textKey: 'panel.supervision.value.refresh_time',
          textParams: {
            n: supervisionFormatSeconds(last.refresh_time),
            api: supervisionFormatSeconds(last.api_time),
          },
        },
        this._t
      ),
    ];
    if (active !== null) {
      const total = last.periphs_total;
      const fraction =
        typeof total === 'number' && total > 0 ? active / total : 0;
      cards.push(
        supervisionValueCardHtml(
          {
            titleKey: 'panel.supervision.card.activity',
            kind: 'gauge',
            fraction,
            value: supervisionFormatCount(active),
            textKey: 'panel.supervision.value.activity',
            textParams: { n: supervisionFormatCount(active) },
          },
          this._t
        )
      );
    }
    const countValue =
      categoryTotal !== null && categoryTotal > 0
        ? categoryTotal
        : last.periphs_total;
    cards.push(
      supervisionValueCardHtml(
        {
          titleKey: 'panel.supervision.card.periphs',
          value: supervisionFormatCount(countValue),
          textKey: categories
            ? 'panel.supervision.value.periphs_categories'
            : 'panel.supervision.value.periphs',
          textParams: categories
            ? {
                total: supervisionFormatCount(countValue),
                n: supervisionFormatCount(
                  Object.values(categories).filter(
                    (count) => typeof count === 'number' && count > 0
                  ).length
                ),
              }
            : {
                total: supervisionFormatCount(last.periphs_total),
                dynamic: supervisionFormatCount(last.periphs_dynamic),
              },
          chips: supervisionCategoryChipsHtml(categories),
        },
        this._t
      )
    );
    if (cpuSeries.length > 0) {
      const cpu = lastFinite(cpuSeries);
      const freeKb = lastFinite(freeSeries);
      cards.push(
        supervisionMetricCardHtml(
          {
            titleKey: 'panel.supervision.card.system',
            kind: 'line',
            series: cpuSeries,
            value: `${supervisionFormatDecimal(cpu)} %`,
            textKey:
              freeKb !== null
                ? 'panel.supervision.value.system'
                : 'panel.supervision.value.system_cpu',
            textParams: {
              cpu: supervisionFormatDecimal(cpu),
              kb: supervisionFormatDecimal(freeKb),
            },
          },
          this._t
        )
      );
    }
    // Story 112: the history-recovery indicator row — conditional on
    // the payload's history key (absent when the option is off). Four
    // value cards, pure display: every number comes from the backend,
    // the panel never recomputes (CAP-9: the panel displays).
    const history =
      box && typeof box.history === 'object' ? box.history : null;
    if (history) {
      const eligible = history.eligible || 0;
      const done = history.completed || 0;
      cards.push(
        supervisionValueCardHtml(
          {
            titleKey: 'panel.supervision.card.history_completion',
            kind: 'gauge',
            fraction: eligible > 0 ? done / eligible : 0,
            value: `${done}/${eligible}`,
            textKey: 'panel.supervision.value.history_completion',
            textParams: { done, total: eligible },
          },
          this._t
        )
      );
      const retrievedPoints = history.retrieved_points || 0;
      const totalPoints = history.total_points;
      cards.push(
        supervisionValueCardHtml(
          {
            titleKey: 'panel.supervision.card.history_points',
            value: supervisionFormatCount(retrievedPoints),
            textKey:
              totalPoints !== null && totalPoints !== undefined
                ? 'panel.supervision.value.history_points'
                : 'panel.supervision.value.history_points_no_estimate',
            textParams: {
              retrieved: supervisionFormatCount(retrievedPoints),
              total: supervisionFormatCount(totalPoints || 0),
            },
          },
          this._t
        )
      );
      const oldestRaw = history.oldest_timestamp;
      const oldest =
        oldestRaw !== null && oldestRaw !== undefined
          ? new Date(oldestRaw)
          : null;
      const oldestValid = oldest !== null && !Number.isNaN(oldest.getTime());
      cards.push(
        supervisionValueCardHtml(
          {
            titleKey: 'panel.supervision.card.history_coverage',
            value: oldestValid
              ? oldest.toLocaleDateString()
              : supervisionFormatCount(null),
            textKey: oldestValid
              ? 'panel.supervision.value.history_coverage'
              : 'panel.supervision.value.history_coverage_empty',
            textParams: {
              date: oldestValid
                ? oldest.toLocaleDateString()
                : String(oldestRaw),
            },
          },
          this._t
        )
      );
      const pending = history.pending || 0;
      const errors = history.errors || 0;
      const eta = history.eta_hours;
      cards.push(
        supervisionValueCardHtml(
          {
            titleKey: 'panel.supervision.card.history_queue',
            value: pending > 0 ? supervisionFormatCount(pending) : '0',
            textKey:
              pending === 0
                ? 'panel.supervision.value.history_queue_empty'
                : eta !== null && eta !== undefined
                  ? 'panel.supervision.value.history_queue'
                  : 'panel.supervision.value.history_queue_no_eta',
            textParams: { pending, errors, eta: String(eta) },
          },
          this._t
        )
      );
    }
    const cardsHtml = cards.join('');
    return `
      <section class="supervision-section">
        <h2>${title}</h2>
        <p class="result-count">${this.t('panel.supervision.cycles', {
          n: cycles.length,
        })}</p>
        <div class="metric-grid">${cardsHtml}</div>
      </section>
    `;
  },

  // ================= Supervision — backfill queue (CAP-5 view) ======

  async _loadBackfill() {
    // Mirror of _loadMetrics: in-flight guard + generation, the raw
    // backend detail stored apart (escaped at render, never t()).
    // The known queue is dropped at load start: a Retry after a
    // refused load re-renders the SKELETON, never a stale queue.
    if (!this._hass || this._backfillLoading) {
      return;
    }
    this._backfillLoading = true;
    this._backfillError = null;
    this._backfillErrorDetail = null;
    this._backfillActionError = null;
    this._confirmIgnore = null;
    this._backfill = null;
    const generation = ++this._backfillGeneration;
    if (this._tab === 'supervision') {
      // Retry shows the skeleton again, never a stale error.
      this._renderSupervisionContent();
    }
    let result = null;
    try {
      result = await this._hass.callWS({
        type: 'eedomus/get_backfill_state',
      });
    } catch (err) {
      result = null;
      if (generation === this._backfillGeneration) {
        this._backfillErrorDetail = (err && (err.message || err.code)) ||
          null;
        this._backfillError = 'panel.common.command_refused';
      }
    }
    this._backfillLoading = false;
    if (generation !== this._backfillGeneration) {
      // A newer load superseded this one: its data is stale, dropped.
      return;
    }
    this._backfill = result || {
      queue: [],
      ignored: [],
      global_paused: false,
      engine_active: false,
    };
    if (this._tab === 'supervision') {
      this._renderSupervisionContent();
    }
  },

  _renderSupervisionContent() {
    const root = this.shadowRoot;
    const content = root && root.getElementById('tab-content');
    if (!content) {
      return;
    }
    // Focus preservation across the swap: the whole #tab-content is
    // rebuilt on every supervision re-render, so a load resolving
    // while the keyboard sits on a queue control would blur the
    // user. The focused control's bf identity is captured before the
    // swap and restored after it through the existing counterpart
    // mapping (the switch resolves through its null periph id).
    const active = root.activeElement;
    const activeAction = active && active.dataset
      ? active.dataset.bfAction || null
      : null;
    const activePeriph = active && active.dataset
      ? active.dataset.bfPeriph || null
      : null;
    content.innerHTML = this._renderSupervisionTab();
    if (activeAction) {
      this._restoreBackfillFocus(activePeriph, activeAction);
    }
  },

  _renderBackfillZone() {
    if (this._backfillError) {
      const detail = this._backfillErrorDetail
        ? this._escapeHtml(this._backfillErrorDetail)
        : this._escapeHtml(this.t(this._backfillError));
      return `
        <section class="backfill-section">
          <h2>${this._escapeHtml(this.t('panel.supervision.backfill.title'))}</h2>
          <div class="state-message" role="alert">
            ${this.t('panel.supervision.backfill.error.load', {
              err: detail,
            })}
            <br>
            <button class="retry" type="button" data-retry="backfill">
              ${this.t('panel.common.retry')}
            </button>
          </div>
        </section>
      `;
    }
    if (this._backfill === null) {
      return this._renderBackfillSkeleton();
    }
    const state = this._backfill || {};
    const queue = state.queue || [];
    const ignored = state.ignored || [];
    if (queue.length === 0 && ignored.length === 0) {
      // Positive empty state (EXPERIENCE l.93): the void is good
      // news, never an error.
      return `
        <section class="backfill-section">
          <h2>${this._escapeHtml(this.t('panel.supervision.backfill.title'))}</h2>
          <div class="state-message">
            ${this.t('panel.supervision.backfill.empty')}
          </div>
        </section>
      `;
    }
    const paused = Boolean(state.global_paused);
    // The global switch heads the queue view (role="switch", the
    // backend does the fan-out); with nothing pending there is
    // nothing to pause — the positive empty state replaces it.
    const switchHtml = queue.length > 0
      ? `
      <button class="backfill-switch" type="button" role="switch"
              data-bf-action="global" data-bf-switch="1"
              aria-checked="${paused}">
        ${this._escapeHtml(this.t('panel.supervision.backfill.global.label'))}
        <span class="backfill-switch-state">
          ${this._escapeHtml(this.t(paused
            ? 'panel.supervision.backfill.global.state_paused'
            : 'panel.supervision.backfill.global.state_resumed'))}
        </span>
      </button>`
      : '';
    const actionErrorHtml = this._backfillActionError
      ? `
      <p class="backfill-alert" role="alert">
        ${this.t('panel.supervision.backfill.feedback.error', {
          name: this._escapeHtml(this._backfillActionError.name || ''),
          err: this._escapeHtml(this._backfillActionError.detail ||
            this.t('panel.common.unknown_error')),
        })}
      </p>`
      : '';
    const rowsHtml = queue
      .map((row) => this._renderBackfillRow(row))
      .join('');
    // An empty queue with ignored rows renders NO all-recovered
    // message — recoveries were abandoned, not recovered: the
    // section title and the ignored sub-section alone.
    const queueBody = queue.length > 0
      ? `<div class="backfill-rows">${rowsHtml}</div>`
      : '';
    const ignoredHtml = ignored.length > 0
      ? this._renderBackfillIgnored(ignored)
      : '';
    return `
      <section class="backfill-section">
        <h2>${this._escapeHtml(this.t('panel.supervision.backfill.title'))}</h2>
        ${actionErrorHtml}
        ${switchHtml}
        ${queueBody}
        ${ignoredHtml}
      </section>
    `;
  },

  _renderBackfillSkeleton() {
    // Skeleton shaped like the expected content: queue lines.
    const row = '<div class="backfill-skeleton-row" aria-hidden="true"></div>';
    return `
      <section class="backfill-section">
        <h2>${this._escapeHtml(this.t('panel.supervision.backfill.title'))}</h2>
        <div role="status" aria-label="${this._escapeHtml(
          this.t('panel.supervision.backfill.skeleton.aria')
        )}">
          <div aria-hidden="true" inert>
            ${row.repeat(4)}
          </div>
        </div>
      </section>
    `;
  },

  _renderBackfillRow(row) {
    const periphId = String(row.periph_id);
    const name = row.name || periphId;
    const status = row.status || '';
    const confirming = this._confirmIgnore === periphId;
    // Pause/Resume follows the row state: a paused row offers the
    // resume, every other row the pause. The token check goes through
    // the status map — the token doubles as an EN catalog label, so
    // it stays a data key (object property), never a literal.
    const pauseAction = BACKFILL_STATUS_KEYS[status] ===
      BACKFILL_STATUS_KEYS.paused
      ? { action: 'resume', labelKey: 'panel.supervision.backfill.action.resume' }
      : { action: 'pause', labelKey: 'panel.supervision.backfill.action.pause' };
    const button = (action, labelKey) => `
          <button class="row-action" type="button"
                  data-bf-action="${action}"
                  data-bf-periph="${this._escapeAttr(periphId)}">
            ${this.t(labelKey)}
          </button>`;
    const detailHtml = status === 'error'
      ? this._renderBackfillErrorDetail(row)
      : '';
    return `
      <div class="backfill-row" data-bf-row="${this._escapeAttr(periphId)}">
        <span class="backfill-name">${this._escapeHtml(name)}</span>
        <span class="backfill-periph">periph_id ${this._escapeHtml(periphId)}</span>
        <span class="backfill-status">${this._escapeHtml(
          supervisionBackfillStatusText(status, this._t)
        )}</span>
        <span class="backfill-position">${this.t(
          'panel.supervision.backfill.row.position',
          { n: row.position != null ? row.position : '—' }
        )}</span>
        ${backfillProgressHtml(row, this._t)}
        ${detailHtml}
        <span class="backfill-actions">
          ${button('retry', 'panel.supervision.backfill.action.retry')}
          ${button('prioritize', 'panel.supervision.backfill.action.prioritize')}
          ${button(pauseAction.action, pauseAction.labelKey)}
          <button class="row-action" type="button"
                  data-bf-action="ignore"
                  data-bf-periph="${this._escapeAttr(periphId)}">
            ${this.t(confirming
              ? 'panel.supervision.backfill.ignore.confirm'
              : 'panel.supervision.backfill.action.ignore')}
          </button>
        </span>
        ${confirming
          ? `
        <p class="backfill-alert" role="alert">
          ${this.t('panel.supervision.backfill.ignore.confirm_message', {
            name: this._escapeHtml(name),
          })}
        </p>`
          : ''}
      </div>
    `;
  },

  _renderBackfillErrorDetail(row) {
    const parts = [];
    const message = row.error_message;
    if (message) {
      // Truncated detail, full message in the title — same contract
      // as the coherence chip (never the title alone).
      parts.push(
        `<span class="backfill-error-detail" title="${this._escapeAttr(message)}">` +
        `${this._escapeHtml(truncateDetailText(message, 40))}</span>`
      );
    } else {
      // No message from the backend: the fallback label keeps the
      // line honest instead of a bare status.
      parts.push(
        `<span class="backfill-error-detail">${this._escapeHtml(
          this.t('panel.supervision.backfill.row.error_fallback')
        )}</span>`
      );
    }
    if (row.attempts != null) {
      parts.push(
        `<span class="backfill-error-detail">${this.t(
          row.attempts === 1
            ? 'panel.supervision.backfill.row.attempts_one'
            : 'panel.supervision.backfill.row.attempts_other',
          { n: row.attempts }
        )}</span>`
      );
    }
    if (row.retry_after) {
      // Readable display text, the full ISO local text in the title.
      parts.push(
        `<span class="backfill-error-detail" title="${this._escapeAttr(
          String(row.retry_after)
        )}">` +
        `${this.t('panel.supervision.backfill.row.retry_after', {
          retry_after: this._escapeHtml(
            supervisionFormatTimestamp(row.retry_after)
          ),
        })}</span>`
      );
    }
    return parts.join(' ');
  },

  _renderBackfillIgnored(ignored) {
    const rows = ignored
      .map((row) => {
        const periphId = String(row.periph_id);
        const name = row.name || periphId;
        return `
      <div class="backfill-row" data-bf-row="${this._escapeAttr(periphId)}">
        <span class="backfill-name">${this._escapeHtml(name)}</span>
        <span class="backfill-periph">periph_id ${this._escapeHtml(periphId)}</span>
        <span class="backfill-actions">
          <button class="row-action" type="button"
                  data-bf-action="reactivate"
                  data-bf-periph="${this._escapeAttr(periphId)}">
            ${this.t('panel.supervision.backfill.action.reactivate')}
          </button>
        </span>
      </div>`;
      })
      .join('');
    return `
      <h3>${this._escapeHtml(this.t('panel.supervision.backfill.ignored.title'))}</h3>
      <div class="backfill-rows">${rows}</div>
    `;
  },

  _backfillQueueRows() {
    return (this._backfill && this._backfill.queue) || [];
  },

  _backfillRowById(periphId) {
    // Queue rows first, then the ignored sub-section (reactivation).
    const state = this._backfill || {};
    const lists = [state.queue, state.ignored];
    for (const list of lists) {
      for (const row of list || []) {
        if (String(row.periph_id) === String(periphId)) {
          return row;
        }
      }
    }
    return null;
  },

  _backfillHasRow(periphId) {
    return this._backfillQueueRows().some(
      (row) => String(row.periph_id) === String(periphId)
    );
  },

  _onSupervisionEvent(ev) {
    const bfButton = ev.target.closest('[data-bf-action]');
    if (!bfButton) {
      return;
    }
    if (bfButton.dataset.bfAction === 'ignore' &&
        this._confirmIgnore !== bfButton.dataset.bfPeriph) {
      // Two-gesture ignore (pointer AND keyboard), historique.js
      // pattern: the first click only swaps the button and shows the
      // inline confirmation — NO network call. Arming another line
      // cancels this one (single confirmation slot).
      this._confirmIgnore = bfButton.dataset.bfPeriph;
      this._renderSupervisionContent();
      // The swapped confirm button takes the focus: Enter executes
      // the second gesture directly (keyboard parity, EXPERIENCE
      // l.134).
      const target = this._focusBackfillControl(
        this._confirmIgnore,
        'ignore'
      );
      if (target && target.focus) {
        target.focus();
      }
      return;
    }
    this._onBackfillAction(bfButton);
  },

  async _onBackfillAction(button) {
    // In-flight guard + generation (mirror of the loads): a double
    // click issues the verb ONCE, and a resolution superseded by a
    // newer action is dropped — a stale state is never written back.
    if (!this._hass || this._backfillActionLoading) {
      return;
    }
    this._backfillActionLoading = true;
    const generation = ++this._backfillActionGen;
    const action = button.dataset.bfAction;
    const periphId = button.dataset.bfPeriph || null;
    const row = periphId != null ? this._backfillRowById(periphId) : null;
    const name = (row && (row.name || row.periph_id)) || periphId || '';
    // A new action clears the previous refusal: the zone never
    // accumulates stale errors.
    this._backfillActionError = null;
    let msg;
    if (action === 'global') {
      // The switch targets the whole engine: the backend owns the
      // per-box fan-out.
      msg = {
        type: 'eedomus/backfill_set_paused',
        global: true,
        paused: !(this._backfill && this._backfill.global_paused),
      };
    } else {
      msg = Object.assign({}, BACKFILL_COMMANDS[action], {
        periph_id: periphId,
      });
    }
    let result = null;
    let failure = null;
    let refused = false;
    try {
      result = await this._hass.callWS(msg);
    } catch (err) {
      // Nominal refusal (busy mono-importer, unknown or completed
      // periph): the queue keeps the last known real state, the
      // refusal is rendered nominatively — never a mute button.
      failure = (err && (err.message || err.code)) || null;
      refused = true;
    }
    const state = result && result.state;
    if (!refused && (!state || !Array.isArray(state.queue))) {
      // The response carries no usable queue state: treated as a
      // refusal too — the known real state is kept and no success is
      // announced (a success announce without a re-rendered state
      // would lie about the queue).
      refused = true;
    }
    this._backfillActionLoading = false;
    if (generation !== this._backfillActionGen) {
      // A newer action superseded this one: its resolution is stale,
      // dropped entirely.
      return;
    }
    if (refused) {
      this._backfillActionError = { name, detail: failure };
      // A failed action voids the pending ignore confirmation: the
      // confirmation is volatile, never carried across a refusal.
      this._confirmIgnore = null;
    } else {
      // The response's {state} re-renders the queue — never a second
      // get_backfill_state round trip.
      this._backfill = state;
      if (this._confirmIgnore != null &&
          !this._backfillHasRow(this._confirmIgnore)) {
        // The confirmed line left the queue: the pending confirmation
        // dies with it.
        this._confirmIgnore = null;
      }
    }
    if (this._tab === 'supervision') {
      this._renderSupervisionContent();
      this._announceBackfillResult(action, name, refused, failure);
      this._restoreBackfillFocus(periphId, action);
    }
  },

  _announceBackfillResult(action, name, refused, detail) {
    const live = this.shadowRoot &&
      this.shadowRoot.getElementById('backfill-status-live');
    if (!live) {
      return;
    }
    let text = '';
    if (refused) {
      text = this.t('panel.supervision.backfill.feedback.error', {
        name,
        err: detail || this.t('panel.common.unknown_error'),
      });
    } else if (action === 'global') {
      const paused = Boolean(this._backfill && this._backfill.global_paused);
      text = this.t('panel.supervision.backfill.feedback.global', {
        state: this.t(paused
          ? 'panel.supervision.backfill.global.state_paused'
          : 'panel.supervision.backfill.global.state_resumed'),
      });
    } else {
      const key = BACKFILL_FEEDBACK_KEYS[action];
      if (key) {
        text = this.t(key, { name });
      }
    }
    if (text) {
      // textContent: the raw backend detail never needs escaping here.
      this._announceStatusNow(live, text);
    }
  },

  _focusBackfillControl(periphId, wantedAction) {
    const root = this.shadowRoot;
    if (!root || !root.querySelectorAll) {
      return null;
    }
    if (periphId == null) {
      return root.querySelector('[data-bf-switch]');
    }
    for (const row of root.querySelectorAll('[data-bf-row]')) {
      if (row.getAttribute('data-bf-row') === String(periphId)) {
        return (wantedAction &&
            row.querySelector(`[data-bf-action="${wantedAction}"]`)) ||
          row.querySelector('button');
      }
    }
    // The row left the view (ignored, completed): the zone's stable
    // control takes the focus — same contract as the coherence
    // "Show all" restoration.
    return root.querySelector('[data-bf-switch]') ||
      root.querySelector('[data-bf-row] button');
  },

  _restoreBackfillFocus(periphId, action) {
    const target = this._focusBackfillControl(
      periphId,
      BACKFILL_FOCUS_ACTION[action]
    );
    if (target && target.focus) {
      target.focus();
    }
  },
  });
}
