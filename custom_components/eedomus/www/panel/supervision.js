/**
 * Supervision tab of the Eedomus config panel (CAP-9).
 *
 * Real ES module imported by www/eedomus-panel.js: the tab's
 * stylesheet chunk and the supervision prototype mixin. One callWS
 * per tab visit (eedomus/get_box_metrics) + Retry — same loading
 * contract as the other lazy tabs: no subscription, no polling.
 *
 * Charts are inline SVG themed through HA CSS variables only — no HA
 * chart component is exposed to the panel context (esbuild internals,
 * version-hashed URLs) and no chart library may be vendored for this
 * (toolchain-free vanilla). Every metric value carries its textual
 * equivalent next to the chart: the chart is never the sole carrier
 * of the information (svg aria-hidden, values readable as text).
 */

import { escapeHtml } from './shared.js';

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
        .metric-skeleton {
          height: 180px;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          opacity: 0.6;
        }
        .supervision-link { margin: 4px 0 12px; }
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
    const sections = boxes
      .map((box, index) => this._renderSupervisionBox(box, index))
      .join('');
    return `
      ${sections}
      <p class="supervision-link">
        <button class="row-action" type="button" data-goto-coherence="1">
          ${this.t('panel.supervision.link.coherence')}
        </button>
      </p>
    `;
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
    const periphSeries = supervisionCycleSeries(cycles, 'periphs_total');
    const callsSeries = supervisionCycleSeries(cycles, 'api_calls');
    // Each card: label + current value + textual equivalent + chart.
    // The equivalent names the numbers — the chart is never the only
    // carrier (Accessibility floor). Value, series and sentence all
    // read from the SAME last cycle record.
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
      supervisionMetricCardHtml(
        {
          titleKey: 'panel.supervision.card.periphs',
          kind: 'line',
          series: periphSeries,
          value: supervisionFormatCount(last.periphs_total),
          textKey: 'panel.supervision.value.periphs',
          textParams: {
            total: supervisionFormatCount(last.periphs_total),
            dynamic: supervisionFormatCount(last.periphs_dynamic),
          },
        },
        this._t
      ),
      supervisionMetricCardHtml(
        {
          titleKey: 'panel.supervision.card.api_calls',
          kind: 'bars',
          series: callsSeries,
          value: supervisionFormatCount(last.api_calls),
          textKey: 'panel.supervision.value.api_calls',
          textParams: {
            n: supervisionFormatCount(last.api_calls),
          },
        },
        this._t
      ),
    ].join('');
    return `
      <section class="supervision-section">
        <h2>${title}</h2>
        <p class="result-count">${this.t('panel.supervision.cycles', {
          n: cycles.length,
        })}</p>
        <div class="metric-grid">${cards}</div>
      </section>
    `;
  },
  });
}
