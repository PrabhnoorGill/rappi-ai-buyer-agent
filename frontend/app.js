const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000"
  : ""; // same-origin if you serve frontend behind a proxy

async function loadState() {
  const res = await fetch(`${API_BASE}/api/state`);
  const data = await res.json();
  const el = document.getElementById("state");
  el.innerHTML = `
    <table>
      <tr><th>Product</th><td>${data.products.map(p => `${p.name} (${p.product_id})`).join(", ")}</td></tr>
      <tr><th>Inventory</th><td>${data.inventory.map(i => `${i.on_hand_qty} units @ ${i.node_id}`).join(", ")}</td></tr>
      <tr><th>Forecast (14d)</th><td>${data.forecasts.map(f => `${f.forecast_qty} units, trend: ${f.trend}`).join(", ")}</td></tr>
      <tr><th>Open POs</th><td>${data.purchase_orders.map(po => `${po.po_id}: ${po.quantity} units (${po.status})`).join(", ") || "none"}</td></tr>
      <tr><th>Supplier</th><td>${data.suppliers.map(s => `${s.name}: MOQ ${s.min_order_qty}, lead ${s.lead_time_days}d, $${s.unit_price}/unit`).join(" | ")}</td></tr>
      <tr><th>Budget</th><td>$${data.budgets.map(b => b.available_amount).join(", ")}</td></tr>
      <tr><th>Storage capacity</th><td>${data.storage.map(s => `${s.available_units} units total`).join(", ")}</td></tr>
    </table>`;
}

document.getElementById("reset-btn").addEventListener("click", async () => {
  await fetch(`${API_BASE}/api/state/reset`, { method: "POST" });
  await loadState();
});

document.getElementById("rec-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const recommendation = {
    product_id: form.get("product_id"),
    node_id: form.get("node_id"),
    supplier_id: form.get("supplier_id"),
    recommended_qty: parseInt(form.get("recommended_qty"), 10),
    category: "default",
  };

  const resultPanel = document.getElementById("result-panel");
  resultPanel.hidden = false;
  document.getElementById("trace").innerHTML = "<em>Running agent…</em>";
  document.getElementById("decision").innerHTML = "";
  document.getElementById("validation").innerHTML = "";

  try {
    const res = await fetch(`${API_BASE}/api/agent/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(recommendation),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "The agent request failed.");
    renderResult(data);
  } catch (error) {
    document.getElementById("trace").innerHTML = "";
    document.getElementById("decision").innerHTML = `<p class="bad">${error.message}</p>`;
    document.getElementById("validation").innerHTML = "";
  } finally {
    await loadState();
  }
});

function renderResult(data) {
  const traceEl = document.getElementById("trace");
  traceEl.innerHTML = data.trace.map(step => {
    if (step.type === "tool_call") {
      return `<div class="step"><span class="name">🔎 ${step.name}</span>(${JSON.stringify(step.input)})
        <pre>${JSON.stringify(step.result, null, 2)}</pre></div>`;
    }
    return `<div class="step"><span class="name">📝 submit_decision</span><pre>${JSON.stringify(step.input, null, 2)}</pre></div>`;
  }).join("");

  const d = data.final_decision;
  const decisionEl = document.getElementById("decision");
  decisionEl.innerHTML = `
    <span class="decision-badge decision-${d.decision}">${d.decision}</span>
    ${d.quantity ? `<span> — <code class="qty">${d.quantity} units</code></span>` : ""}
    <p>${d.reasoning}</p>
    <ul>${d.key_factors.map(f => `<li>${f}</li>`).join("")}</ul>
    ${data.decision_history.length > 1 ? `<p><em>Revised ${data.decision_history.length - 1} time(s) after failing validation.</em></p>` : ""}
  `;

  const v = data.validation;
  const a = data.action_result;
  let html = `<p><strong>Pre-execution validation:</strong> <span class="${v.passed ? "ok" : "bad"}">${v.passed ? "PASSED" : "FAILED"}</span></p>`;
  if (v.violations.length) {
    html += `<ul>${v.violations.map(x => `<li class="bad">${x}</li>`).join("")}</ul>`;
  }
  if (a) {
    html += `<p><strong>Action taken:</strong> created ${a.purchase_order.po_id} for ${a.purchase_order.quantity} units.</p>`;
    html += `<p><strong>Post-execution validation:</strong> <span class="${a.execution_validation.passed ? "ok" : "bad"}">${a.execution_validation.passed ? "PASSED" : "FAILED"}</span></p>`;
  } else {
    html += `<p><strong>Action taken:</strong> none (decision was ${d.decision}).</p>`;
  }
  if (data.escalated) {
    html += `<p class="escalated">⚠️ Escalated for human review.</p>`;
  }
  document.getElementById("validation").innerHTML = html;
}

loadState();
