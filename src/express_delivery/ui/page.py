"""Page unique de l'IHM (dans le module pour être embarquée dans l'image sans package-data)."""

PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Livraison express</title>
<style>
  :root { --bg:#f6f7f9; --panel:#fff; --text:#1d2330; --muted:#6b7280; --line:#e3e6eb;
          --accent:#2457d6; --yes:#11845b; --no:#c2410c; --sel:#eaf0ff; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14171c; --panel:#1c2027; --text:#e7e9ee; --muted:#9aa3b2; --line:#2c323c;
            --accent:#7aa2ff; --yes:#3ccf91; --no:#ff8a4c; --sel:#253049; }
  }
  * { box-sizing: border-box; }
  body { margin:0; font:15px/1.4 system-ui, sans-serif; background:var(--bg); color:var(--text); }
  header { padding:14px 20px; border-bottom:1px solid var(--line); display:flex; gap:12px;
           align-items:baseline; flex-wrap:wrap; }
  header h1 { font-size:18px; margin:0; }
  header span { color:var(--muted); font-size:13px; }
  main { display:grid; grid-template-columns:minmax(260px, 1fr) 2fr; gap:16px; padding:16px;
         height:calc(100vh - 56px); }
  section { background:var(--panel); border:1px solid var(--line); border-radius:10px;
            overflow:hidden; display:flex; flex-direction:column; min-height:0; }
  section h2 { font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted);
               margin:0; padding:12px 16px; border-bottom:1px solid var(--line); }
  ul { list-style:none; margin:0; padding:0; overflow-y:auto; }
  li { padding:9px 16px; border-bottom:1px solid var(--line); cursor:pointer; display:flex;
       justify-content:space-between; gap:8px; }
  li:hover { background:var(--sel); }
  li.current { background:var(--sel); box-shadow:inset 3px 0 var(--accent); }
  li.done { color:var(--muted); }
  li.new { animation:flash 1.5s ease-out; }
  @keyframes flash { from { background:var(--sel); } }
  li small { color:var(--muted); }
  .tag { font-size:12px; font-weight:600; }
  .tag.oui { color:var(--yes); } .tag.non { color:var(--no); }
  #detail { padding:20px; overflow-y:auto; flex:1; }
  .verdict { display:flex; align-items:center; gap:20px; margin:4px 0 20px; }
  .badge { font-size:40px; font-weight:800; padding:8px 26px; border-radius:12px; color:#fff; }
  .badge.oui { background:var(--yes); } .badge.non { background:var(--no); }
  .bar { height:8px; background:var(--line); border-radius:4px; width:220px; overflow:hidden; }
  .bar div { height:100%; background:var(--accent); }
  dl { display:grid; grid-template-columns:repeat(auto-fill, minmax(170px, 1fr)); gap:12px 20px;
       margin:0 0 20px; }
  dt { color:var(--muted); font-size:12px; } dd { margin:0; font-weight:600; }
  footer { padding:12px 16px; border-top:1px solid var(--line); display:flex;
           justify-content:space-between; align-items:center; gap:12px; }
  button { font:inherit; font-weight:600; padding:10px 22px; border:0; border-radius:8px;
           background:var(--accent); color:#fff; cursor:pointer; }
  button:disabled { opacity:.45; cursor:default; }
  .muted { color:var(--muted); }
  @media (max-width: 720px) { main { grid-template-columns:1fr; height:auto; }
                              ul { max-height:40vh; } }
</style>
</head>
<body>
<header><h1>Livraison express</h1><span id="status">Chargement…</span></header>
<main>
  <section>
    <h2>Commandes qui arrivent</h2>
    <ul id="orders"></ul>
  </section>
  <section>
    <h2>Commande à traiter</h2>
    <div id="detail"><p class="muted">En attente de commandes…</p></div>
    <footer><span id="position" class="muted"></span><button id="next" disabled>Suivant →</button></footer>
  </section>
</main>
<script>
const FIELDS = [
  ["order_date", "Date", v => v ? v.slice(0, 10) : "—"], ["hour", "Heure", v => v + " h"],
  ["distance_km", "Distance", v => v + " km"], ["weight_kg", "Poids", v => v + " kg"],
  ["order_value_eur", "Valeur", v => v + " €"], ["delivery_zone", "Zone"], ["weather", "Météo"],
  ["customer_type", "Client"], ["stock_available", "Stock", v => v ? "disponible" : "rupture"],
  ["preparation_time_min", "Préparation", v => v == null ? "—" : v + " min"],
  ["carrier_capacity", "Capacité transporteur", v => Math.round(v * 100) + " %"],
];
const orders = [];          // ordre d'arrivée
const decisions = {};       // order_id -> "oui" | "non"
let current = -1;
const $ = id => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = Object.assign(document.createElement(tag), attrs);
  node.append(...children);
  return node;
}

async function poll() {
  try {
    const response = await fetch("api/orders?limit=50");
    if (!response.ok) throw new Error(response.status);
    const known = new Set(orders.map(o => o.order_id));
    const fresh = (await response.json()).filter(o => !known.has(o.order_id));
    orders.push(...fresh);
    $("status").textContent = `${orders.length} commandes · mise à jour ${new Date().toLocaleTimeString()}`;
    renderList(new Set(fresh.map(o => o.order_id)));
    if (current < 0 && orders.length) select(0);
    updateNext();
  } catch (error) {
    $("status").textContent = "Lecture des commandes impossible (" + error.message + "), nouvel essai…";
  }
}

function renderList(fresh = new Set()) {
  const list = $("orders");
  list.replaceChildren(...orders.map((o, i) => {
    const d = decisions[o.order_id];
    return el("li", {
      className: [i === current && "current", d && "done", fresh.has(o.order_id) && "new"].filter(Boolean).join(" "),
      onclick: () => select(i),
    },
      el("span", {}, o.order_id, el("br"), el("small", {}, `${o.delivery_zone} · ${o.distance_km} km`)),
      d ? el("span", { className: "tag " + d }, d.toUpperCase()) : el("span"));
  }).reverse());   // la plus récente en haut
}

async function select(index) {
  current = index;
  renderList();
  updateNext();
  const order = orders[index];
  $("detail").replaceChildren(el("p", { className: "muted" }, "Prédiction de " + order.order_id + "…"));
  try {
    const response = await fetch(`api/orders/${encodeURIComponent(order.order_id)}/prediction`);
    if (!response.ok) throw new Error((await response.json()).detail || response.status);
    const p = await response.json();
    if (orders[current] !== order) return;   // l'opérateur est déjà passé à une autre commande
    decisions[order.order_id] = p.decision;
    renderList();
    $("detail").replaceChildren(
      el("h3", {}, order.order_id),
      el("div", { className: "verdict" },
        el("div", { className: "badge " + p.decision }, p.decision.toUpperCase()),
        el("div", {},
          el("div", {}, "Probabilité express : ", el("b", {}, Math.round(p.probability * 100) + " %")),
          el("div", { className: "bar" }, el("div", { style: `width:${p.probability * 100}%` })),
          el("small", { className: "muted" }, "Modèle " + p.model_version))),
      el("dl", {}, ...FIELDS.flatMap(([key, label, fmt]) =>
        [el("dt", {}, label), el("dd", {}, fmt ? fmt(p.order[key]) : String(p.order[key]))])));
  } catch (error) {
    $("detail").replaceChildren(el("p", {}, "Prédiction impossible : " + error.message));
  }
}

function updateNext() {
  const last = current >= orders.length - 1;
  $("next").disabled = current < 0 || last;
  $("next").textContent = last && current >= 0 ? "En attente de la prochaine commande…" : "Suivant →";
  $("position").textContent = current >= 0 ? `${current + 1} / ${orders.length}` : "";
}

$("next").onclick = () => select(current + 1);
poll();
setInterval(poll, 5000);
</script>
</body>
</html>
"""
