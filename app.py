import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from poker.aggregator import StatAggregator
from poker.models import Source
from poker.normalizer import HandNormalizer
from poker.parser import HandParser

app = FastAPI()

parser = HandParser()
normalizer = HandNormalizer()
aggregator = StatAggregator()
stat_catalog = json.loads(Path("stat_catalog.json").read_text())


def load_hands():
    parsed = []

    # Prefer explicit demo files when present.
    population_demo = Path("data/1.txt")
    gto_demo = Path("data/10.txt")
    if population_demo.exists() and gto_demo.exists():
        parsed += parser.parse_file(population_demo, Source.POPULATION)
        parsed += parser.parse_file(gto_demo, Source.GTO)
    else:
        # Fallback: reuse the same data directories contract as main.py.
        gto_directory = Path(os.environ["GTO_DATA_DIR"])
        population_directory = Path(os.environ["POPULATION_DATA_DIR"])

        for file_path in sorted(gto_directory.glob("*.txt"))[:2]:
            parsed += parser.parse_file(file_path, Source.GTO)
        for file_path in sorted(population_directory.glob("*.txt"))[:5]:
            parsed += parser.parse_file(file_path, Source.POPULATION)

    normalized = []
    for hand in parsed:
        normalized.extend(normalizer.normalize(hand))

    return normalized


HANDS = load_hands()


def apply_filters(hands, spot=None, formation=None, position=None, role=None):
    result = hands

    if spot:
        result = [h for h in result if h.spot.value == spot]

    if formation:
        result = [h for h in result if h.formation and h.formation.value == formation]

    if position:
        result = [h for h in result if h.hero_position.value == position]

    if role:
        result = [h for h in result if h.hero_role.value == role]

    return result


@app.get("/stats")
def get_stats(
    spot: Optional[str] = Query(None),
    formation: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
):
    filtered = apply_filters(HANDS, spot, formation, position, role)
    results = aggregator.aggregate(filtered, stat_catalog)
    stat_by_id = {s["id"]: s for s in stat_catalog}
    payload = []
    for result in results:
        row = result.to_dict()
        stat_meta = stat_by_id.get(result.stat_id, {})
        row["description"] = stat_meta.get("description", "")
        row["opportunity"] = stat_meta.get("opportunity", {})
        row["success"] = stat_meta.get("success", {})
        row["contextFilters"] = stat_meta.get("contextFilters", {})
        row["spot"] = stat_meta.get("spot")
        row["formation"] = stat_meta.get("formation")
        row["position"] = stat_meta.get("position")
        row["role"] = stat_meta.get("role")
        row["street"] = stat_meta.get("street")
        payload.append(row)
    return payload


@app.get("/debug/{stat_id}")
def debug(stat_id: str):
    stat = next(s for s in stat_catalog if s["id"] == stat_id)

    population = [h for h in HANDS if h.source.value == "population"]
    gto = [h for h in HANDS if h.source.value == "gto"]

    context_filters = stat.get("contextFilters") or {}

    def format_hand(hand):
        return {
            "id": hand.hand_id,
            "line": hand.line,
        }

    def collect(hands):
        denom = []
        num = []

        for hand in hands:
            ok = True

            if (
                context_filters.get("spot")
                and hand.spot.value != context_filters["spot"]
            ):
                ok = False
            if context_filters.get("formation") and (
                hand.formation is None
                or hand.formation.value != context_filters["formation"]
            ):
                ok = False
            if (
                context_filters.get("position")
                and hand.hero_position.value != context_filters["position"]
            ):
                ok = False
            if (
                context_filters.get("role")
                and hand.hero_role.value != context_filters["role"]
            ):
                ok = False

            if ok:
                denom.append(hand)

                success_action = (stat.get("success") or {}).get("action")
                if (
                    success_action
                    and hand.action
                    and hand.action.value == success_action
                ):
                    num.append(hand)

        return {
            "denominator": [format_hand(hand) for hand in denom],
            "numerator": [format_hand(hand) for hand in num],
        }

    return {
        "population": collect(population),
        "gto": collect(gto),
    }


@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
<style>
body { font-family: Arial; padding: 20px; }
table { border-collapse: collapse; width: 100%; }
td, th { border: 1px solid #ccc; padding: 6px; }
tr:hover { background: #f5f5f5; cursor: pointer; }
.low { color: orange; }
.ok { color: green; }
.positive { color: green; font-weight: 700; }
.negative { color: red; font-weight: 700; }
.neutral { color: gray; font-weight: 700; }
.hand-id-list {
  font-family: monospace;
  padding: 4px;
  margin: 4px 0 12px 0;
  max-height: 100px;
  overflow-y: auto;
  word-wrap: break-word;
  background: #f9f9f9;
  border: 1px solid #eee;
}
details summary {
  cursor: pointer;
  margin-bottom: 8px;
}
</style>
</head>
<body>

<h2>Poker Stats Explorer</h2>

<div>
  Spot:
  <select id="spot">
    <option value="">All</option>
    <option value="SRP">SRP</option>
    <option value="3BP">3BP</option>
  </select>

  Formation:
  <select id="formation">
    <option value="">All</option>
    <option value="BB_BTN">BB_BTN</option>
    <option value="BB_SB">BB_SB</option>
  </select>

  Position:
  <select id="position">
    <option value="">All</option>
    <option value="IP">IP</option>
    <option value="OOP">OOP</option>
  </select>

  Role:
  <select id="role">
    <option value="">All</option>
    <option value="PFR">PFR</option>
    <option value="PFC">PFC</option>
  </select>

  <button onclick="loadStats()">Apply</button>
</div>

<br>

<table id="stats"></table>

<br>
<button onclick="toggleDebug()">Show debug</button>
<div id="debug" style="display:none;"></div>

<script>
let selectedStatId = null;

function formationLabel(formation) {
  if (formation === "BB_BTN") return "BB vs BTN";
  if (formation === "BB_SB") return "BB vs SB";
  return "-";
}

function statStructure(contextFilters) {
  const spot = contextFilters?.spot || "-";
  const formation = formationLabel(contextFilters?.formation || "");
  const position = contextFilters?.position || "-";
  const role = contextFilters?.role || "-";
  return `[${spot} | ${formation} | ${position} | ${role}]`;
}

function statContext(stat) {
  const ctx = stat.contextFilters || {};
  const merged = {
    spot: ctx.spot || stat.spot || "-",
    formation: ctx.formation || stat.formation || "",
    position: ctx.position || stat.position || "-",
    role: ctx.role || stat.role || "-",
  };
  return statStructure(merged);
}

function calcNumerator(value, denominator) {
  if (value === null || denominator === 0) return 0;
  return Math.round(value * denominator);
}

function formatStat(value, numerator, denominator) {
  if (denominator === 0 || value === null) {
    return `NO DATA<br><span class="sample">sample: ${denominator}</span>`;
  }
  const percent = (value * 100).toFixed(1);
  return `${percent}% (${numerator} / ${denominator})`;
}

function formatDelta(delta) {
  if (delta === null) return "NO DATA";
  const deltaPercent = (delta * 100).toFixed(1);
  return `${delta > 0 ? "+" : ""}${deltaPercent}%`;
}

function deltaClass(delta) {
  if (delta === null) return "neutral";
  if (delta > 0) return "positive";
  if (delta < 0) return "negative";
  return "neutral";
}

function tooltipText(stat) {
  const opportunity = stat.opportunity ? JSON.stringify(stat.opportunity) : "n/a";
  const success = stat.success ? JSON.stringify(stat.success) : "n/a";
  return `${stat.label}\\n${stat.description || ""}\\nOpportunity: ${opportunity}\\nSuccess: ${success}`;
}

function escapeAttr(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function loadStats() {
  const spot = document.getElementById("spot").value;
  const formation = document.getElementById("formation").value;
  const position = document.getElementById("position").value;
  const role = document.getElementById("role").value;

  fetch(`/stats?spot=${spot}&formation=${formation}&position=${position}&role=${role}`)
    .then(r => r.json())
    .then(data => {
      const table = document.getElementById("stats");

      table.innerHTML = `
        <tr>
          <th>Stat</th>
          <th>Pop</th>
          <th>GTO</th>
          <th>Delta</th>
        </tr>
      `;

      data.forEach(s => {
        const row = document.createElement("tr");
        const popNum = calcNumerator(s.population.value, s.population.sample);
        const gtoNum = calcNumerator(s.gto.value, s.gto.sample);

        row.innerHTML = `
          <td title="${escapeAttr(tooltipText(s))}">
            <div><b>${s.label}</b></div>
            <div class="sample">${statContext(s)}</div>
          </td>
          <td>${formatStat(s.population.value, popNum, s.population.sample)}</td>
          <td>${formatStat(s.gto.value, gtoNum, s.gto.sample)}</td>
          <td class="${deltaClass(s.delta)}">${formatDelta(s.delta)}</td>
        `;

        row.onclick = () => {
          selectedStatId = s.stat_id;
          if (document.getElementById("debug").style.display !== "none") {
            loadDebug(selectedStatId);
          }
        };

        table.appendChild(row);
      });
    });
}

function renderHands(hands) {
  const shown = hands.slice(0, 10);
  const more = hands.length - shown.length;
  const lines = shown.map(h => `${h.id} → ${h.line}`);
  if (more > 0) {
    lines.push(`... + ${more} more`);
  }
  return lines.join("<br>");
}

function loadDebug(stat_id) {
  fetch(`/debug/${stat_id}`)
    .then(r => r.json())
    .then(data => {
      document.getElementById("debug").innerHTML = `
        <details open>
          <summary><b>${stat_id}</b></summary>
          <div>
            <b>Population (denominator):</b>
            <div class="hand-id-list">${renderHands(data.population.denominator)}</div>
          </div>
          <div>
            <b>Population (numerator):</b>
            <div class="hand-id-list">${renderHands(data.population.numerator)}</div>
          </div>
          <div>
            <b>GTO (denominator):</b>
            <div class="hand-id-list">${renderHands(data.gto.denominator)}</div>
          </div>
          <div>
            <b>GTO (numerator):</b>
            <div class="hand-id-list">${renderHands(data.gto.numerator)}</div>
          </div>
        </details>
      `;
    });
}

function toggleDebug() {
  const el = document.getElementById("debug");
  if (el.style.display === "none") {
    el.style.display = "block";
    if (selectedStatId) {
      loadDebug(selectedStatId);
    } else {
      el.innerHTML = "<i>Select a stat row to see debug.</i>";
    }
  } else {
    el.style.display = "none";
  }
}

loadStats();
</script>

</body>
</html>
"""
