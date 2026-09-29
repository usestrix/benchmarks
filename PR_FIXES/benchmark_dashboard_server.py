#!/usr/bin/env python3
"""Serve a portable live dashboard for verified-fix benchmark runs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(os.environ["STRIX_BENCHMARK_OUTPUT"]).expanduser().resolve()
RESULTS = ROOT / "results"
CASES = ROOT / "cases"
LOG_PATH = Path(
    os.environ.get("BENCHMARK_LOG", ROOT / "benchmark.log")
).expanduser().resolve()
START = int(os.environ.get("BENCHMARK_START", "1"))
TOTAL = int(os.environ.get("BENCHMARK_TOTAL", "100"))
NUMBERS = list(range(START, START + TOTAL))
STARTED_AT_TEXT = os.environ["BENCHMARK_STARTED_AT"]
STARTED_AT = datetime.fromisoformat(
    STARTED_AT_TEXT.replace("Z", "+00:00")
).timestamp()

MAX_ACTIVITY = 30
MAX_EVENTS = 40
MAX_LOG_LINES = 120
MAX_OUTPUT_LENGTH = 800
EVENT_HISTORY: dict[int, list[dict[str, str]]] = {}
EVENT_SIGNATURES: dict[int, tuple[Any, ...]] = {}
EVENT_LOCK = threading.Lock()


PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#090c11">
  <title>Verified-fix benchmark dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      --background: #000000;
      --foreground: #ffffff;
      --card: #0a0a0a;
      --muted: #a3a3a3;
      --border: rgba(255, 255, 255, .12);
      --input: rgba(255, 255, 255, .06);
      --ring: rgba(255, 255, 255, .72);
      background: var(--background);
      color: var(--foreground);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body { margin: 0; background: var(--background); color: var(--foreground); }
    button, summary { touch-action: manipulation; }
    :focus-visible { outline: 2px solid var(--ring); outline-offset: 3px; }
    .skip {
      position: fixed; left: 16px; top: 12px; z-index: 10; padding: 10px 14px;
      border-radius: 10px; background: var(--foreground); color: var(--background);
      transform: translateY(-180%);
    }
    .skip:focus { transform: translateY(0); }
    main { width: min(1600px, calc(100% - 32px)); margin: 32px auto 72px; }
    header { display: flex; justify-content: space-between; gap: 24px; align-items: end; }
    .header-tools {
      display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap;
    }
    .control {
      min-height: 32px; padding: 6px 10px; border: 1px solid var(--border);
      border-radius: 7px; background: var(--input); color: var(--foreground);
      font: 600 12px/1.2 Inter, ui-sans-serif, system-ui, sans-serif;
      cursor: pointer;
    }
    .control:hover { border-color: rgba(255, 255, 255, .28); color: var(--foreground); }
    h1 { margin: 5px 0 0; font-size: clamp(30px, 5vw, 52px); letter-spacing: -.045em; }
    h2 { margin: 0 0 14px; font-size: 18px; scroll-margin-top: 20px; }
    .muted { color: var(--muted); }
    .live { display: inline-flex; align-items: center; gap: 8px; color: #91f2c3; }
    .dot { width: 9px; height: 9px; border-radius: 50%; background: #42d392; box-shadow: 0 0 16px #42d392; }
    .progress {
      height: 12px; margin: 30px 0 18px; border: 1px solid var(--border);
      border-radius: 999px; overflow: hidden; background: var(--input);
    }
    .bar {
      height: 100%; width: 0; background: var(--foreground);
      transition: width .25s ease;
    }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .metric, .panel, .case-card {
      border: 1px solid var(--border); border-radius: 16px; background: var(--card);
    }
    .metric { padding: 18px; }
    .metric-value { margin-top: 5px; font-size: 30px; font-weight: 600; font-variant-numeric: tabular-nums; }
    .panel { margin-top: 18px; padding: 18px; }
    .cases { margin-top: 18px; display: grid; gap: 10px; overflow-anchor: none; }
    .case-card { min-width: 0; overflow: hidden; }
    .case-card[open] { border-color: rgba(255, 255, 255, .3); }
    .case-card summary {
      min-height: 96px; padding: 16px; cursor: pointer; list-style: none;
      display: grid; gap: 10px;
    }
    .case-card summary::-webkit-details-marker { display: none; }
    .case-head { display: flex; align-items: start; justify-content: space-between; gap: 12px; }
    .case-title { min-width: 0; display: flex; align-items: center; gap: 10px; }
    .case-number {
      display: grid; place-items: center; flex: 0 0 36px; height: 36px;
      border-radius: 10px; background: #1b2330; color: #dce4f3;
      font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums;
    }
    .repository { min-width: 0; font-weight: 600; overflow-wrap: anywhere; }
    .stage { color: #dbe3ef; font-size: 14px; }
    .latest { min-width: 0; color: #9ba7b8; font-size: 13px; overflow-wrap: anywhere; }
    .status {
      flex: 0 0 auto; border: 1px solid currentColor; border-radius: 999px;
      padding: 5px 9px; font-size: 12px; font-weight: 600; text-transform: uppercase;
      letter-spacing: .045em;
    }
    .status-running { color: #aebeff; }
    .status-ready { color: #91f2c3; }
    .status-needs_review { color: #ffdc80; }
    .status-blocked { color: #ffb4ba; }
    .status-failed, .status-runtime_error { color: #ff8996; }
    .status-queued { color: #8490a1; }
    .case-progress { height: 5px; overflow: hidden; border-radius: 99px; background: #202938; }
    .case-progress span { display: block; height: 100%; background: #6c8cff; }
    .case-body { border-top: 1px solid var(--border); padding: 18px; display: grid; gap: 18px; }
    .section { min-width: 0; }
    .section h3 {
      margin: 0 0 8px; color: #cbd5e4; font-size: 12px; text-transform: uppercase;
      letter-spacing: .07em;
    }
    .chips { display: flex; flex-wrap: wrap; gap: 7px; }
    .chip {
      max-width: 100%; padding: 5px 8px; border: 1px solid #303c4e;
      border-radius: 8px; background: #171e29; color: #c9d3e2; font-size: 12px;
      overflow-wrap: anywhere;
    }
    .activity, .events, .gaps { display: grid; gap: 7px; }
    .events {
      max-height: 280px; overflow: auto; overscroll-behavior: contain; padding-right: 4px;
    }
    .flow-graph { display: grid; gap: 10px; padding: 2px; }
    .flow-row {
      min-width: 0; display: grid; gap: 8px;
    }
    .flow-row-label {
      color: #8996a8; font-size: 12px; font-weight: 600; letter-spacing: .05em;
      text-transform: uppercase;
    }
    .flow-track {
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
      align-items: stretch; gap: 8px; min-width: 0;
    }
    .flow-node {
      min-width: 0; padding: 11px; border: 1px solid #303c4e;
      border-radius: 12px; background: #0d1219;
    }
    .flow-node-head {
      display: flex; align-items: center; justify-content: space-between; gap: 10px;
    }
    .flow-node-title { min-width: 0; font-size: 12px; font-weight: 600; overflow-wrap: anywhere; }
    .flow-node-agent {
      margin-top: 3px; color: #8595aa; font-size: 12px; letter-spacing: .05em;
      text-transform: uppercase;
    }
    .flow-node-meta, .flow-node-detail {
      margin-top: 7px; color: #aab6c6; font-size: 12px; line-height: 1.45;
      overflow-wrap: anywhere;
    }
    .flow-node-detail { color: #8996a8; }
    .summary-flow {
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px;
    }
    .summary-stage {
      min-width: 0; display: flex; align-items: center; gap: 7px; padding: 7px 9px;
      border: 1px solid #303c4e; border-radius: 8px; background: #0d1219;
      color: #aab6c6; font-size: 12px;
    }
    .summary-stage::before {
      content: ""; flex: 0 0 auto; width: 7px; height: 7px; border-radius: 50%;
      background: #8490a1;
    }
    .summary-stage-passed::before { background: #42d392; }
    .summary-stage-running::before {
      background: #7f97ff; box-shadow: 0 0 10px #7f97ff;
    }
    .summary-stage-failed::before { background: #f05d6c; }
    .summary-stage-warning::before, .summary-stage-blocked::before { background: #e6b94f; }
    .terminal-stack { display: grid; gap: 12px; }
    .terminal-panel {
      min-width: 0; border: 1px solid #303c4e; border-radius: 12px;
      background: #080b10; overflow: hidden;
    }
    .terminal-head {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      padding: 10px 12px; border-bottom: 1px solid #26303e; background: #0d1219;
      color: #cbd5e4; font-size: 12px; font-weight: 600;
    }
    .terminal-output {
      height: 360px; margin: 0; padding: 14px; overflow: auto;
      overscroll-behavior: contain; background: #080b10; color: #c2cedd;
      font: 12px/1.55 ui-monospace, SFMono-Regular, Consolas, monospace;
      white-space: pre; tab-size: 2;
    }
    .flow-state {
      flex: 0 0 auto; display: inline-flex; align-items: center; gap: 5px;
      color: #aab6c6; font-size: 12px; font-weight: 600; text-transform: uppercase;
      letter-spacing: .04em;
    }
    .flow-state::before {
      content: ""; width: 7px; height: 7px; border-radius: 50%; background: #8490a1;
    }
    .flow-state-passed, .flow-state-ready { color: #91f2c3; }
    .flow-state-passed::before, .flow-state-ready::before { background: #42d392; }
    .flow-state-warning, .flow-state-blocked { color: #ffdc80; }
    .flow-state-warning::before, .flow-state-blocked::before { background: #e6b94f; }
    .flow-state-failed, .flow-state-rejected { color: #ff9aa5; }
    .flow-state-failed::before, .flow-state-rejected::before { background: #f05d6c; }
    .flow-state-running { color: #aebeff; }
    .flow-state-running::before {
      background: #7f97ff; box-shadow: 0 0 10px #7f97ff;
    }
    .flow-connector { display: none; }
    .activity {
      max-height: 320px; overflow-y: auto; overscroll-behavior: contain;
      padding-right: 4px;
    }
    .activity-row, .event-row, .gap-row {
      min-width: 0; padding: 9px 10px; border: 1px solid #26303e;
      border-radius: 10px; background: #0d1219; font-size: 12px;
    }
    .activity-head {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
    }
    .section-toggle {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      min-height: 32px; cursor: pointer; list-style: none; color: #cbd5e4;
      font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .07em;
    }
    .section-toggle::-webkit-details-marker { display: none; }
    .section-toggle::after {
      content: "+"; flex: 0 0 auto; color: #91a2b9; font-size: 16px; line-height: 1;
    }
    .activity-panel[open] > .section-toggle::after { content: "−"; }
    .section-toggle-meta {
      margin-left: auto; color: #8996a8; font-size: 12px; font-weight: 500;
      text-transform: none; letter-spacing: 0; font-variant-numeric: tabular-nums;
    }
    .activity-panel .activity { margin-top: 8px; }
    .activity-name { min-width: 0; font-weight: 600; overflow-wrap: anywhere; }
    .activity-meta { flex: 0 0 auto; color: #9ba7b8; font-variant-numeric: tabular-nums; }
    .command, .output, .log {
      margin-top: 6px; color: #aab6c6; font: 12px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace;
      white-space: pre-wrap; overflow-wrap: anywhere;
    }
    .output {
      max-height: 220px; overflow: auto; overscroll-behavior: contain;
      padding: 8px; border-radius: 8px; background: #080b10;
    }
    .event-row {
      display: grid; grid-template-columns: 108px 88px minmax(0, 1fr);
      gap: 10px; align-items: baseline;
    }
    .event-time {
      color: #c2cedd; font: 12px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace;
      font-variant-numeric: tabular-nums;
    }
    .event-kind { color: #8595aa; text-transform: uppercase; font-size: 12px; letter-spacing: .05em; }
    .gap-row { border-color: #56373d; color: #ffc1c7; }
    .two-column { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .empty { color: #758195; font-size: 12px; }
    .log-panel summary { cursor: pointer; font-weight: 600; }
    .log {
      height: 280px; overflow: auto; margin: 14px 0 0; padding: 14px;
      border-radius: 10px; background: #080b10; font-size: 12px;
      white-space: pre; tab-size: 2;
    }
    .footer { margin-top: 20px; font-size: 12px; }
    @media (max-width: 820px) {
      header { align-items: start; flex-direction: column; }
      .metrics, .two-column { grid-template-columns: 1fr; }
      .flow-track { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .summary-flow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 520px) {
      .flow-track { grid-template-columns: 1fr; }
      .summary-flow { grid-template-columns: 1fr; }
      .event-row { grid-template-columns: 78px minmax(0, 1fr); }
      .event-kind { display: none; }
    }
    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      .bar { transition: none; }
    }
  </style>
</head>
<body>
  <a class="skip" href="#cases">Skip to cases</a>
  <main>
    <header>
      <div>
        <div class="live"><span class="dot" aria-hidden="true"></span>Live replay</div>
        <h1>Verified-fix benchmark</h1>
      </div>
      <div class="header-tools">
        <div class="muted" id="updated">Loading…</div>
        <button class="control" id="live-toggle" type="button" aria-pressed="true">Pause updates</button>
        <button class="control" id="refresh-now" type="button">Refresh now</button>
      </div>
    </header>
    <div class="progress" aria-label="Completed benchmark cases">
      <div class="bar" id="bar"></div>
    </div>
    <section class="metrics" aria-label="Benchmark summary">
      <div class="metric"><div class="muted">Completed</div><div class="metric-value" id="completed">—</div></div>
      <div class="metric"><div class="muted">Running</div><div class="metric-value" id="running">—</div></div>
      <div class="metric"><div class="muted">Ready</div><div class="metric-value" id="ready">—</div></div>
      <div class="metric"><div class="muted">Blocked / failed</div><div class="metric-value" id="blocked">—</div></div>
    </section>
    <details class="panel log-panel" open>
      <summary>Live runner log</summary>
      <pre class="log" id="runner-log">No runner log lines yet.</pre>
    </details>
    <section id="cases" class="cases" aria-label="Benchmark cases"></section>
    <p class="footer muted">
      Runtime states are not correctness scores. Result JSON files are the authoritative benchmark records.
    </p>
  </main>
  <script>
    const casesRoot = document.querySelector("#cases");
    const liveToggle = document.querySelector("#live-toggle");
    const refreshNow = document.querySelector("#refresh-now");
    let liveUpdates = true;
    let refreshing = false;
    const escapeHtml = value => String(value ?? "")
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;").replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
    const formatSeconds = value => {
      const seconds = Math.max(0, Math.round(Number(value || 0)));
      const minutes = Math.floor(seconds / 60);
      return minutes ? `${minutes}m ${seconds % 60}s` : `${seconds}s`;
    };
    const label = value => String(value || "unknown").replaceAll("_", " ");
    const renderChips = items => items.length
      ? `<div class="chips">${items.map(item => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>`
      : `<div class="empty">None recorded.</div>`;
    const renderActivity = (items, number) => items.length
      ? `<div class="activity">${items.map(item => `
          <div class="activity-row">
            <div class="activity-head">
              <div class="activity-name">${escapeHtml(item.category)} · ${escapeHtml(item.name)}</div>
              <div class="activity-meta">${escapeHtml(label(item.status))}${item.duration_seconds != null ? ` · ${formatSeconds(item.duration_seconds)}` : ""}</div>
            </div>
          </div>`).join("")}</div>`
      : `<div class="empty">No tool activity is available yet.</div>`;
    const renderEvents = items => items.length
      ? `<div class="events">${items.map(item => `
          <div class="event-row">
            <time class="event-time" datetime="${escapeHtml(item.timestamp || "")}">${escapeHtml(item.time || "—")}</time>
            <div class="event-kind">${escapeHtml(item.kind)}</div>
            <div>${escapeHtml(item.message)}</div>
          </div>`).join("")}</div>`
      : `<div class="empty">No events are available yet.</div>`;
    const renderGaps = items => items.length
      ? `<div class="gaps">${items.map(item => `<div class="gap-row">${escapeHtml(item)}</div>`).join("")}</div>`
      : `<div class="empty">No blocker or required gap is recorded.</div>`;
    const renderFlowNode = node => `
      <div class="flow-node" role="listitem">
        <div class="flow-node-head">
          <div class="flow-node-title">${escapeHtml(node.title)}</div>
          <span class="flow-state flow-state-${escapeHtml(node.status)}">${escapeHtml(label(node.status))}</span>
        </div>
        <div class="flow-node-agent">${escapeHtml(node.agent)}</div>
        ${node.meta ? `<div class="flow-node-meta">${escapeHtml(node.meta)}</div>` : ""}
      </div>`;
    const renderFlowTrack = nodes => `
      <div class="flow-track" role="list">
        ${nodes.map((node, index) => `
          ${index ? `<div class="flow-connector" aria-hidden="true">→</div>` : ""}
          ${renderFlowNode(node)}
        `).join("")}
      </div>`;
    const renderTerminal = (attempt, caseNumber) => {
      const nodes = [attempt.patch, attempt.compile, attempt.unit, attempt.verify];
      const outputs = nodes.filter(node => node.log);
      return outputs.length ? `
        <div class="terminal-stack">
          ${outputs.map(node => `
            <section class="terminal-panel">
              <div class="terminal-head">
                <span>${escapeHtml(node.title)} output</span>
                <span class="flow-state flow-state-${escapeHtml(node.status)}">${escapeHtml(label(node.status))}</span>
              </div>
              <pre class="terminal-output" id="terminal-${caseNumber}-${attempt.number}-${escapeHtml(node.title)}" tabindex="0" translate="no">${escapeHtml(node.log)}</pre>
            </section>`).join("")}
        </div>` : "";
    };
    const renderFlow = (flow, caseNumber) => `
      <div class="flow-graph" aria-label="Repair agent workflow">
        ${flow.attempts.map(attempt => `
          <div class="flow-row">
            <div class="flow-row-label">Attempt ${escapeHtml(attempt.number)}</div>
            ${renderFlowTrack([attempt.patch, attempt.compile, attempt.unit, attempt.verify])}
            ${renderTerminal(attempt, caseNumber)}
          </div>
        `).join("")}
      </div>`;
    const renderSummaryFlow = flow => {
      const attempt = flow.attempts.at(-1);
      if (!attempt) return "";
      return `<div class="summary-flow" aria-label="Latest attempt stage status">
        ${[attempt.patch, attempt.compile, attempt.unit, attempt.verify].map(node => `
          <div class="summary-stage summary-stage-${escapeHtml(node.status)}">
            <span>${escapeHtml(node.title.replace(/^[1-4]\.\s*/, ""))}: ${escapeHtml(label(node.status))}</span>
          </div>`).join("")}
      </div>`;
    };
    const renderCase = (item, isOpen) => `
      <details class="case-card" id="case-${item.number}" ${isOpen ? "open" : ""}>
        <summary>
          <div class="case-head">
            <div class="case-title">
              <span class="case-number">${escapeHtml(item.label)}</span>
              <div class="repository">${escapeHtml(item.repository || "Waiting for request")}</div>
            </div>
            <span class="status status-${escapeHtml(item.state)}">${escapeHtml(label(item.state))}</span>
          </div>
          <div class="stage">${escapeHtml(item.stage)} · ${formatSeconds(item.elapsed_seconds)}</div>
          <div class="latest">${escapeHtml(item.latest_event)}</div>
          ${renderSummaryFlow(item.flow)}
        </summary>
        <div class="case-body">
          <div class="section">
            <h3>Fix progress</h3>
            ${renderFlow(item.flow, item.number)}
          </div>
          <div class="section">
            <h3>Case event log</h3>
            ${renderEvents(item.events)}
          </div>
        </div>
      </details>`;
    async function refresh() {
      if (refreshing) return;
      refreshing = true;
      try {
        const response = await fetch("/api/status", {cache: "no-store"});
        const data = await response.json();
        document.querySelector("#completed").textContent = `${data.completed}/${data.total}`;
        document.querySelector("#running").textContent = data.running;
        document.querySelector("#ready").textContent = data.counts.ready || 0;
        document.querySelector("#blocked").textContent =
          (data.counts.blocked || 0) + (data.counts.failed || 0) +
          (data.counts.runtime_error || 0);
        document.querySelector("#bar").style.width = `${data.total ? (data.completed / data.total) * 100 : 0}%`;
        document.querySelector("#updated").textContent =
          `Updated ${new Intl.DateTimeFormat(undefined, {timeStyle: "medium"}).format(new Date(data.updated_at))}`;
        const existingCards = [...document.querySelectorAll(".case-card")];
        const openCases = new Set(
          [...document.querySelectorAll(".case-card[open]")].map(node => node.id)
        );
        const firstRunning = data.cases.find(item => item.state === "running")?.number;
        const terminalScroll = new Map(
          [...document.querySelectorAll(".terminal-output")].map(node => [
            node.id,
            {top: node.scrollTop, left: node.scrollLeft, follow: node.scrollHeight - node.scrollTop - node.clientHeight < 48}
          ])
        );
        const runnerLog = document.querySelector("#runner-log");
        const runnerScroll = {
          top: runnerLog.scrollTop,
          left: runnerLog.scrollLeft,
          follow: runnerLog.scrollHeight - runnerLog.scrollTop - runnerLog.clientHeight < 48
        };
        const pageScroll = document.scrollingElement.scrollTop;
        casesRoot.innerHTML = data.cases.map(
          item => renderCase(
            item,
            openCases.has(`case-${item.number}`) ||
              (!existingCards.length && item.number === firstRunning)
          )
        ).join("");
        document.scrollingElement.scrollTop = pageScroll;
        requestAnimationFrame(() => {
          document.scrollingElement.scrollTop = pageScroll;
          document.querySelectorAll(".terminal-output").forEach(node => {
            const saved = terminalScroll.get(node.id);
            if (!saved) {
              node.scrollTop = node.scrollHeight;
              return;
            }
            node.scrollTop = saved.follow ? node.scrollHeight : saved.top;
            node.scrollLeft = saved.left;
          });
        });
        runnerLog.textContent =
          data.runner_log.length ? data.runner_log.join("\n") : "No runner log lines yet.";
        runnerLog.scrollTop = runnerScroll.follow ? runnerLog.scrollHeight : runnerScroll.top;
        runnerLog.scrollLeft = runnerScroll.left;
      } catch (error) {
        document.querySelector("#updated").textContent = `Dashboard error: ${error}`;
      } finally {
        refreshing = false;
      }
    }
    liveToggle.addEventListener("click", () => {
      liveUpdates = !liveUpdates;
      liveToggle.setAttribute("aria-pressed", String(liveUpdates));
      liveToggle.textContent = liveUpdates ? "Pause updates" : "Resume updates";
      if (liveUpdates) refresh();
    });
    refreshNow.addEventListener("click", refresh);
    refresh();
    setInterval(() => {
      if (liveUpdates) refresh();
    }, 3000);
  </script>
</body>
</html>
"""


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _truncate(value: Any, length: int = MAX_OUTPUT_LENGTH) -> str:
    text = str(value or "").strip()
    if len(text) <= length:
        return text
    return f"{text[: length - 1]}…"


def _tail_text(value: Any, length: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) <= length:
        return text
    return f"…{text[-(length - 1):]}"


def _tail_lines(path: Path, limit: int) -> list[str]:
    try:
        with path.open("rb") as source:
            source.seek(0, os.SEEK_END)
            size = source.tell()
            source.seek(max(0, size - 256_000))
            text = source.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    return text.splitlines()[-limit:]


def _result_path(number: int) -> Path | None:
    for path in (RESULTS / f"{number:02d}.json", RESULTS / f"{number}.json"):
        try:
            if path.is_file() and path.stat().st_mtime >= STARTED_AT:
                return path
        except OSError:
            continue
    return None


def _case_path(number: int) -> Path:
    padded = CASES / f"{number:02d}"
    return padded if padded.exists() else CASES / str(number)


def _request(case_path: Path) -> dict[str, Any]:
    return _read_json(case_path / "request.json") or {}


def _workspace_changes(workspace: Path) -> list[str]:
    if not (workspace / ".git").is_dir():
        return []
    try:
        completed = subprocess.run(  # noqa: S603
            ["/usr/bin/git", "status", "--short", "--untracked-files=all"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    files: list[str] = []
    for line in completed.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and path not in files:
            files.append(path)
    return files[:30]


def _check_activity(
    category: str, checks: list[dict[str, Any]], activity: list[dict[str, Any]]
) -> None:
    for check in checks:
        argv = check.get("argv")
        command = " ".join(str(item) for item in argv) if isinstance(argv, list) else ""
        activity.append(
            {
                "category": category,
                "name": check.get("name") or "Command",
                "status": check.get("status") or "unknown",
                "duration_seconds": check.get("duration_seconds"),
                "command": command,
                "output": _truncate(check.get("output")),
            }
        )


def _stage_check_summary(
    checks: list[dict[str, Any]], label: str
) -> tuple[str, str]:
    statuses = Counter(str(check.get("status") or "unknown") for check in checks)
    required_failures = sum(
        bool(check.get("required")) and check.get("status") != "passed"
        for check in checks
    )
    if not checks:
        return "skipped", "No validation commands were recorded."
    if required_failures:
        status = "failed"
    elif statuses.get("failed") or statuses.get("error"):
        status = "warning"
    else:
        status = "passed"
    parts = [f"{statuses.get('passed', 0)}/{len(checks)} {label} passed"]
    parts.extend(
        f"{count} {status.replace('_', ' ')}"
        for status, count in statuses.items()
        if status != "passed" and count
    )
    return status, " · ".join(parts)


def _flow_graph(record: dict[str, Any]) -> dict[str, Any]:
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    changed_files = result.get("changed_files") or []
    changed_count = len(changed_files) if isinstance(changed_files, list) else 0
    attempts = result.get("attempt_history") or record.get("attempt_history") or []
    flow_attempts: list[dict[str, Any]] = []
    if isinstance(attempts, list):
        for position, attempt in enumerate(attempts):
            if not isinstance(attempt, dict):
                continue
            number = attempt.get("attempt") or position + 1
            repair = (
                attempt.get("repair")
                if isinstance(attempt.get("repair"), dict)
                else {}
            )
            repair_raw_status = str(repair.get("status") or "unknown")
            empty_completion = (
                repair_raw_status == "complete"
                and any(
                    "No changed files were found" in str(gap)
                    for gap in repair.get("gaps") or []
                )
            )
            if empty_completion:
                repair_status = "failed"
                repair_meta = "No files changed."
            elif repair_raw_status == "complete":
                repair_status = "passed"
                repair_meta = f"{changed_count} file(s) changed."
            elif repair_raw_status == "budget_exhausted":
                repair_status = "warning"
                repair_meta = "Ran out of budget before handoff."
            else:
                repair_status = "failed"
                repair_meta = repair_raw_status.replace("_", " ")

            checks = attempt.get("checks") or []
            if not isinstance(checks, list):
                checks = []
            compile_checks = [
                check
                for check in checks
                if check.get("purpose") == "quality" and check.get("required") is True
            ]
            unit_checks = [
                check
                for check in checks
                if check.get("purpose") == "unit" and check.get("required") is True
            ]
            regression_checks = [
                check
                for check in checks
                if check.get("purpose") == "regression"
                and check.get("required") is True
            ]
            compile_status, compile_meta = _stage_check_summary(
                compile_checks, "compile checks"
            )
            unit_status, unit_meta = _stage_check_summary(
                unit_checks, "unit checks"
            )
            test_plan = (
                repair.get("test_plan")
                if isinstance(repair.get("test_plan"), dict)
                else {}
            )
            if not unit_checks and test_plan.get("no_unit_tests_reason"):
                unit_meta = _truncate(test_plan["no_unit_tests_reason"], 180)

            verifier = (
                attempt.get("verifier")
                if isinstance(attempt.get("verifier"), dict)
                else {}
            )
            decision = str(verifier.get("decision") or "not_reached")
            if decision == "verified":
                verify_status = (
                    "passed"
                    if all(check.get("status") == "passed" for check in regression_checks)
                    and bool(regression_checks)
                    else "warning"
                )
            elif decision == "rejected":
                verify_status = "failed"
            else:
                verify_status = (
                    "failed"
                    if any(check.get("status") != "passed" for check in regression_checks)
                    else "skipped"
                )
            regression_passed = sum(
                check.get("status") == "passed" for check in regression_checks
            )
            verify_meta = (
                f"Regression {regression_passed}/{len(regression_checks)} passed"
                f" · review {decision.replace('_', ' ')}"
                f" · invariant closed {bool(verifier.get('security_invariant_closed'))}"
                if verifier
                else (
                    f"Regression {regression_passed}/{len(regression_checks)} passed"
                    " · reviewer not reached"
                )
            )
            verify_detail = (
                verifier.get("summary")
                or ((verifier.get("gaps") or [None])[0])
                or "No verification evidence was recorded."
            )

            flow_attempts.append(
                {
                    "number": number,
                    "patch": {
                        "title": "1. Build patch",
                        "agent": "Repair agent",
                        "status": repair_status,
                        "meta": repair_meta,
                        "detail": _truncate(
                            repair.get("summary")
                            or repair.get("blocker")
                            or "No repair summary was recorded.",
                            240,
                        ),
                    },
                    "compile": {
                        "title": "2. Compile fix",
                        "agent": "Repair agent",
                        "status": compile_status,
                        "meta": compile_meta,
                        "detail": _truncate(
                            compile_checks[0].get("name")
                            if compile_checks
                            else "No compile or quality check was recorded.",
                            180,
                        ),
                    },
                    "unit": {
                        "title": "3. Run unit tests",
                        "agent": "Repair agent",
                        "status": unit_status,
                        "meta": unit_meta,
                        "detail": _truncate(
                            unit_checks[0].get("name")
                            if unit_checks
                            else "No unit-test execution was recorded.",
                            180,
                        ),
                        "log": _tail_text(
                            "\n\n".join(
                                f"$ {' '.join(str(arg) for arg in check.get('argv', []))}\n"
                                f"{check.get('output') or ''}"
                                for check in unit_checks
                            )
                        ),
                    },
                    "verify": {
                        "title": "4. Verify fix worked",
                        "agent": "Reviewer agent",
                        "status": verify_status,
                        "meta": verify_meta,
                        "detail": _truncate(verify_detail, 240),
                    },
                }
            )
    return {"attempts": flow_attempts}


def _live_flow(
    stage: str,
    latest_event: str,
    state: str = "running",
    observed_phase: str | None = None,
    live_log: str = "",
) -> dict[str, Any]:
    running = state == "running"
    patch_status = "running" if running else "pending"
    patch_meta = stage
    patch_detail = latest_event if running else "Waiting for an execution slot."
    compile_status = "pending"
    compile_meta = "Waiting for patch."
    unit_status = "pending"
    unit_meta = "Waiting for compilation."
    verify_status = "pending"
    verify_meta = "Waiting for tests."
    if observed_phase in {"compile", "unit", "verify"}:
        patch_status = "passed"
        patch_meta = "Patch submitted."
        patch_detail = latest_event
    if observed_phase == "compile":
        compile_status = "running"
        compile_meta = stage
    elif observed_phase == "unit":
        compile_meta = "No compile result recorded yet."
        unit_status = "running"
        unit_meta = stage
    elif observed_phase == "verify":
        compile_status = "passed"
        compile_meta = "Compilation completed."
        unit_status = "passed"
        unit_meta = "Customer unit tests completed."
        verify_status = "running"
        verify_meta = stage
    return {
        "attempts": [
            {
                "number": 1,
                "patch": {
                    "title": "1. Build patch",
                    "agent": "Repair agent",
                    "status": patch_status,
                    "meta": patch_meta,
                    "detail": patch_detail,
                },
                "compile": {
                    "title": "2. Compile fix",
                    "agent": "Repair agent",
                    "status": compile_status,
                    "meta": compile_meta,
                    "detail": "",
                },
                "unit": {
                    "title": "3. Run unit tests",
                    "agent": "Repair agent",
                    "status": unit_status,
                    "meta": unit_meta,
                    "detail": "",
                    "log": live_log if observed_phase == "unit" else "",
                },
                "verify": {
                    "title": "4. Verify fix worked",
                    "agent": "Reviewer agent",
                    "status": verify_status,
                    "meta": verify_meta,
                    "detail": "",
                },
            }
        ]
    }


def _recorded_live_flow(
    progress: dict[str, Any], runtime_snapshot: dict[str, str]
) -> dict[str, Any]:
    stages = (
        progress.get("stages")
        if isinstance(progress.get("stages"), dict)
        else {}
    )
    current_stage = str(progress.get("current_stage") or "")
    live_stage = runtime_snapshot.get("stage")
    live_log = runtime_snapshot.get("log", "")
    definitions = (
        ("patch", "1. Build patch", "Repair agent"),
        ("compile", "2. Compile fix", "Repair agent"),
        ("unit", "3. Run unit tests", "Repair agent"),
        ("verify", "4. Verify fix worked", "Reviewer agent"),
    )
    nodes: dict[str, dict[str, Any]] = {}
    for key, title, agent in definitions:
        recorded = stages.get(key) if isinstance(stages.get(key), dict) else {}
        nodes[key] = {
            "title": title,
            "agent": agent,
            "status": recorded.get("status") or "pending",
            "meta": recorded.get("meta") or "",
            "detail": recorded.get("detail") or "",
            "log": live_log if key == current_stage == live_stage else "",
        }
    return {
        "attempts": [
            {
                "number": progress.get("attempt") or 1,
                **nodes,
            }
        ]
    }


def _active_runtime_snapshots() -> dict[str, dict[str, str]]:
    snapshots: dict[str, dict[str, str]] = {}
    try:
        containers = subprocess.run(
            ["docker", "ps", "-q"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return snapshots
    script = (
        'case_label=$(cat /workspace/.strix-benchmark/case 2>/dev/null || true); '
        'stage=$(cat /workspace/.strix-benchmark/stage 2>/dev/null || true); '
        '[ -n "$case_label" ] && [ -n "$stage" ] || exit 0; '
        'printf "%s\\n%s\\n" "$case_label" "$stage"; '
        'tail -c 12000 "/workspace/.strix-benchmark/$stage.log" 2>/dev/null || true'
    )
    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    for container in containers:
        try:
            output = subprocess.run(
                ["docker", "exec", container, "sh", "-c", script],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        lines = output.splitlines()
        if len(lines) < 2:
            continue
        label, stage = lines[:2]
        snapshots[label.zfill(2)] = {
            "stage": stage,
            "log": ansi.sub("", "\n".join(lines[2:])[-12000:]),
        }
    return snapshots


def _active_runtime_phase() -> tuple[str | None, str]:
    if TOTAL != 1:
        return None, ""
    try:
        containers = subprocess.run(
            ["docker", "ps", "-q"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.split()
        commands = "\n".join(
            subprocess.run(
                ["docker", "top", container, "-eo", "pid,args"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout
            for container in containers
        )
    except (OSError, subprocess.SubprocessError):
        return None, ""
    if re.search(
        r"\b(vitest|jest|pytest|phpunit|go test|cargo test|npm run test|pnpm run test|yarn test|bun test)\b",
        commands,
        re.IGNORECASE,
    ):
        return "unit", "A customer unit-test command is running in the sandbox."
    if re.search(
        r"\b(tsc|typecheck|type-check|build|lint|mypy|ruff|cargo check|go vet)\b",
        commands,
        re.IGNORECASE,
    ):
        return "compile", "A compile or repository quality command is running in the sandbox."
    return None, ""


def _record_details(record: dict[str, Any]) -> dict[str, Any]:
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    activity: list[dict[str, Any]] = []
    events: list[dict[str, str]] = []
    started = record.get("started_at")
    if started:
        events.append({"kind": "start", "message": f"Case started at {started}."})

    setup_checks = result.get("setup_checks") or []
    if isinstance(setup_checks, list):
        _check_activity("setup", setup_checks, activity)
        for check in setup_checks:
            events.append(
                {
                    "kind": "setup",
                    "message": (
                        f"{check.get('name') or 'Setup check'}: "
                        f"{check.get('status') or 'unknown'}."
                    ),
                }
            )

    attempts = result.get("attempt_history") or record.get("attempt_history") or []
    if isinstance(attempts, list):
        for index, attempt in enumerate(attempts, start=1):
            if not isinstance(attempt, dict):
                continue
            repair = attempt.get("repair") if isinstance(attempt.get("repair"), dict) else {}
            events.append(
                {
                    "kind": "repair",
                    "message": (
                        f"Attempt {index}: {repair.get('status') or 'unknown'}"
                        f" after {repair.get('turns_used') or 0} turns."
                    ),
                }
            )
            command_results = repair.get("command_results") or []
            if isinstance(command_results, list):
                _check_activity("repair", command_results, activity)

    checks = result.get("checks") or []
    if isinstance(checks, list):
        _check_activity("repository", checks, activity)
        for check in checks:
            events.append(
                {
                    "kind": "check",
                    "message": (
                        f"{check.get('name') or 'Repository check'}: "
                        f"{check.get('status') or 'unknown'}."
                    ),
                }
            )

    verifier = result.get("verifier") if isinstance(result.get("verifier"), dict) else {}
    security_tests = verifier.get("security_tests") or []
    regression_tests = verifier.get("regression_tests") or []
    for category, tests in (
        ("security", security_tests),
        ("regression", regression_tests),
    ):
        if isinstance(tests, list):
            _check_activity(category, tests, activity)
    if verifier:
        events.append(
            {
                "kind": "verifier",
                "message": (
                    f"Verifier decision: {verifier.get('decision') or 'unknown'}. "
                    f"Invariant closed: {bool(verifier.get('security_invariant_closed'))}."
                ),
            }
        )

    state = result.get("state") or (
        "runtime_error" if record.get("runtime_exception") else "unknown"
    )
    events.append({"kind": "finish", "message": f"Case finished with state {state}."})

    verifier_evidence = [
        f"Decision: {verifier.get('decision') or 'not recorded'}",
        f"Invariant closed: {bool(verifier.get('security_invariant_closed'))}",
        f"Reproduction executed: {bool(verifier.get('reproduction_executed'))}",
        f"Harnesses: {len(verifier.get('harnesses') or [])}",
        f"Regression tests: {len(regression_tests) if isinstance(regression_tests, list) else 0}",
        f"Security tests: {len(security_tests) if isinstance(security_tests, list) else 0}",
    ]

    gaps: list[str] = []
    for value in (
        result.get("blocker"),
        verifier.get("blocker"),
        record.get("runtime_exception", {}).get("message")
        if isinstance(record.get("runtime_exception"), dict)
        else None,
    ):
        if value:
            gaps.append(_truncate(value))
    for values in (result.get("gaps"), verifier.get("gaps")):
        if isinstance(values, list):
            gaps.extend(_truncate(value) for value in values if value)

    return {
        "activity": activity[-MAX_ACTIVITY:],
        "events": events[-MAX_EVENTS:],
        "flow": _flow_graph(record),
        "verifier_evidence": verifier_evidence,
        "gaps": list(dict.fromkeys(gaps)),
        "latest_event": events[-1]["message"] if events else "Result recorded.",
    }


def _case_log_lines(number: int, runner_log: list[str]) -> list[str]:
    label = f"{number:02d}"
    patterns = (
        re.compile(rf"\bbenchmark-{number:03d}\b", re.IGNORECASE),
        re.compile(rf"\bcase[\s:#-]*0*{number}\b", re.IGNORECASE),
        re.compile(rf"^\s*{label}:", re.IGNORECASE),
    )
    return [
        line
        for line in runner_log
        if any(pattern.search(line) for pattern in patterns)
    ][-20:]


def _case_status(
    number: int,
    now: float,
    runner_log: list[str],
    runtime_phase: str | None,
    runtime_detail: str,
    runtime_snapshots: dict[str, dict[str, str]],
) -> dict[str, Any]:
    label = f"{number:02d}"
    case_path = _case_path(number)
    request = _request(case_path)
    candidate = request.get("candidate") if isinstance(request.get("candidate"), dict) else {}
    finding = candidate.get("finding") if isinstance(candidate.get("finding"), dict) else {}
    source_identity = (
        candidate.get("source_identity")
        if isinstance(candidate.get("source_identity"), dict)
        else {}
    )
    repository = request.get("repository_id") or source_identity.get("repository")
    security_invariant = candidate.get("security_invariant") or finding.get("description") or ""
    result_path = _result_path(number)
    workspace = case_path / "workspace"
    changed_files: list[str] = []
    case_logs = _case_log_lines(number, runner_log)
    incomplete_result = False

    if result_path:
        record = _read_json(result_path)
        result = (
            record.get("result")
            if isinstance(record, dict) and isinstance(record.get("result"), dict)
            else {}
        )
        final_state = result.get("state") or (
            "runtime_error"
            if isinstance(record, dict) and record.get("runtime_exception")
            else None
        )
        incomplete_result = not final_state
    else:
        record = None
        result = {}
        final_state = None

    if isinstance(record, dict) and final_state:
        result = record.get("result") if isinstance(record.get("result"), dict) else {}
        details = _record_details(record)
        state = final_state
        repository = record.get("repository_full_name") or repository
        candidate_record = record.get("candidate")
        if isinstance(candidate_record, dict):
            security_invariant = candidate_record.get("security_invariant") or security_invariant
        changed_items = result.get("changed_files") or []
        if isinstance(changed_items, list):
            for item in changed_items:
                if isinstance(item, dict):
                    value = item.get("path") or item.get("file")
                else:
                    value = item
                if value:
                    changed_files.append(str(value))
        elapsed = float(
            record.get("wall_clock_seconds")
            or result.get("elapsed_seconds")
            or 0
        )
        return {
            "number": number,
            "label": label,
            "state": state,
            "stage": "Finished",
            "progress": 100,
            "elapsed_seconds": elapsed,
            "repository": repository,
            "security_invariant": _truncate(security_invariant, 1000),
            "changed_files": changed_files[:30],
            **details,
        }

    if case_path.exists():
        try:
            times = [case_path.stat().st_mtime]
            request_path = case_path / "request.json"
            if request_path.exists():
                times.append(request_path.stat().st_mtime)
            case_started = min(value for value in times if value >= STARTED_AT)
        except (OSError, ValueError):
            case_started = STARTED_AT
        elapsed = now - case_started
        if workspace.exists():
            changed_files = _workspace_changes(workspace)
            if changed_files:
                stage = "Repairing and validating"
                progress = 55
                latest_event = f"Workspace has {len(changed_files)} changed file(s)."
            elif request:
                stage = "Repair agent running"
                progress = 35
                latest_event = "The request and frozen workspace are ready."
            else:
                stage = "Preparing source"
                progress = 15
                latest_event = "The frozen workspace is being prepared."
        elif request:
            stage = "Starting isolated runtime"
            progress = 25
            latest_event = "The fix request is ready."
        else:
            stage = "Preparing case"
            progress = 10
            latest_event = "The case output directory was created."
        if incomplete_result:
            latest_event = "An incomplete result file was ignored while the case continues."
        progress_record = _read_json(case_path / "progress.json") or {}
        runtime_snapshot = runtime_snapshots.get(label, {})
        observed_phase = runtime_phase if (case_path / "prepared-fix.zip").exists() else None
        if progress_record:
            current_stage = str(progress_record.get("current_stage") or "patch")
            stage = {
                "patch": "Build patch",
                "compile": "Compile fix",
                "unit": "Run unit tests",
                "verify": "Verify fix worked",
            }.get(current_stage, "Repairing and validating")
            latest_event = str(progress_record.get("latest_event") or latest_event)
            progress = {"patch": 30, "compile": 55, "unit": 75, "verify": 90}.get(
                current_stage, progress
            )
            flow = _recorded_live_flow(progress_record, runtime_snapshot)
        elif observed_phase:
            stage = {
                "compile": "Compile fix",
                "unit": "Run unit tests",
                "verify": "Verify fix worked",
            }[observed_phase]
            latest_event = runtime_detail
            progress = {"compile": 55, "unit": 75, "verify": 90}[observed_phase]
            flow = _live_flow(
                stage,
                latest_event,
                observed_phase=observed_phase,
                live_log=runtime_snapshot.get("log", ""),
            )
        else:
            flow = _live_flow(stage, latest_event)
        events = [
            {"kind": "progress", "message": latest_event},
            *({"kind": "log", "message": line} for line in case_logs),
        ]
        return {
            "number": number,
            "label": label,
            "state": "running",
            "stage": stage,
            "progress": progress,
            "elapsed_seconds": elapsed,
            "repository": repository,
            "security_invariant": _truncate(security_invariant, 1000),
            "changed_files": changed_files,
            "verifier_evidence": ["Verification is still running."],
            "activity": [],
            "flow": flow,
            "gaps": [],
            "events": events[-MAX_EVENTS:],
            "latest_event": case_logs[-1] if case_logs else latest_event,
        }

    return {
        "number": number,
        "label": label,
        "state": "queued",
        "stage": "Queued",
        "progress": 0,
        "elapsed_seconds": 0,
        "repository": repository,
        "security_invariant": _truncate(security_invariant, 1000),
        "changed_files": [],
        "verifier_evidence": [],
        "activity": [],
        "flow": _live_flow("Queued", "Waiting for an execution slot.", "queued"),
        "gaps": [],
        "events": [],
        "latest_event": "Waiting for an execution slot.",
    }


def status() -> dict[str, Any]:
    now = time.time()
    runner_log = _tail_lines(LOG_PATH, MAX_LOG_LINES)
    runtime_phase, runtime_detail = _active_runtime_phase()
    runtime_snapshots = _active_runtime_snapshots()
    cases = [
        _case_status(
            number,
            now,
            runner_log,
            runtime_phase,
            runtime_detail,
            runtime_snapshots,
        )
        for number in NUMBERS
    ]
    with EVENT_LOCK:
        for case in cases:
            attempts = case.get("flow", {}).get("attempts", [])
            attempt = attempts[-1] if attempts else {}
            signature = (
                case.get("state"),
                case.get("stage"),
                case.get("latest_event"),
                attempt.get("number"),
                *(attempt.get(key, {}).get("status") for key in ("patch", "compile", "unit", "verify")),
            )
            number = int(case["number"])
            if EVENT_SIGNATURES.get(number) != signature:
                timestamp = datetime.now(timezone.utc)
                EVENT_HISTORY.setdefault(number, []).append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "time": timestamp.strftime("%H:%M:%S UTC"),
                        "kind": str(case.get("stage") or case.get("state") or "progress"),
                        "message": str(case.get("latest_event") or "Status updated."),
                    }
                )
                EVENT_HISTORY[number] = EVENT_HISTORY[number][-MAX_EVENTS:]
                EVENT_SIGNATURES[number] = signature
            case["events"] = list(EVENT_HISTORY.get(number, []))
    counts: Counter[str] = Counter(case["state"] for case in cases)
    completed = sum(
        case["state"] not in {"queued", "running"} for case in cases
    )
    return {
        "cases": cases,
        "completed": completed,
        "counts": dict(counts),
        "running": counts["running"],
        "total": TOTAL,
        "runner_log": runner_log,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            body = json.dumps(status()).encode()
            content_type = "application/json"
        elif path == "/":
            body = PAGE.encode()
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8787"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(  # noqa: T201
        f"Benchmark dashboard: http://0.0.0.0:{port} "
        f"(output={ROOT}, cases={START}-{START + TOTAL - 1})",
        flush=True,
    )
    server.serve_forever()
