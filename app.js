// ============================================================
// Macro Dashboard - ส่วนหน้าเว็บ
// แต่ละหน้าโหลดข้อมูลของตัวเองแยกกัน ถ้าหน้าไหนพัง หน้าอื่นยังใช้ได้
// ============================================================

// ---------------- ปัดเปลี่ยนหน้า ----------------
(function setupPager() {
  const pager = document.getElementById("pager");
  const tabs = [...document.querySelectorAll("#tabs button")];
  const dots = [...document.querySelectorAll("#dots span")];

  function current() {
    return Math.round(pager.scrollLeft / pager.clientWidth);
  }
  function go(i) {
    i = Math.max(0, Math.min(tabs.length - 1, i));
    pager.scrollTo({ left: i * pager.clientWidth, behavior: "smooth" });
  }
  function mark() {
    const i = current();
    tabs.forEach((b, k) => b.classList.toggle("active", k === i));
    dots.forEach((d, k) => d.classList.toggle("on", k === i));
    try { localStorage.setItem("macro-page", String(i)); } catch (e) {}
  }

  tabs.forEach((b) => b.addEventListener("click", () => go(+b.dataset.page)));
  pager.addEventListener("scroll", () => requestAnimationFrame(mark), { passive: true });
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") go(current() + 1);
    if (e.key === "ArrowLeft") go(current() - 1);
  });
  window.addEventListener("resize", () => go(current()));

  // จำหน้าที่เปิดค้างไว้ล่าสุด
  try {
    const saved = +localStorage.getItem("macro-page");
    if (saved > 0) setTimeout(() => {
      pager.style.scrollBehavior = "auto";
      pager.scrollLeft = saved * pager.clientWidth;
      pager.style.scrollBehavior = "";
      mark();
    }, 0);
  } catch (e) {}
})();

// ---------------- ตัวช่วยจัดรูปแบบ ----------------
const fmt = (n, d = 2) =>
  n == null ? "–" : Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

function thaiDate(s) {
  if (!s) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
  if (!m) return s; // ข้อความวันที่แบบอื่น แสดงตามต้นฉบับ
  const d = new Date(+m[1], +m[2] - 1, +m[3]);
  return d.toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" });
}

// วันที่แบบสั้น เช่น "13 พ.ย. 69" (ใช้ในตารางดัชนีให้พอดีจอมือถือ)
function thaiDateShort(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || "");
  if (!m) return s || "";
  const d = new Date(+m[1], +m[2] - 1, +m[3]);
  return d.toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "2-digit" });
}

function thaiDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("th-TH", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    timeZone: "Asia/Bangkok",
  }) + " น.";
}

// ชื่อย่อในตาราง (ให้พอดีจอมือถือ)
const SHORT = { spx: "S&P 500", nasdaq: "NASDAQ", set: "SET", hscei: "HSCEI", sse: "SSE", vni: "VN-Index" };
// แตะชื่อดัชนี -> เปิดหน้ากราฟของดัชนีนั้นใน TradingView
// ใช้หน้า /symbols/ (แยกหน้าละดัชนี) เพราะหน้า /chart/ จะจำดัชนีที่เปิดล่าสุดไว้ แล้วเปิดตัวเดิมซ้ำ
const TV = { spx: "SP-SPX", nasdaq: "NASDAQ-IXIC", set: "SET-SET", hscei: "HSI-HSCEI", sse: "SSE-000001", vni: "HOSE-VNINDEX" };
const tvLink = (id) => `https://th.tradingview.com/symbols/${TV[id]}/`;
const CUR = { USD: "$", THB: "฿", HKD: "HK$", CNY: "¥", VND: "₫" };

function fmtCap(v, cur) {
  const sym = CUR[cur] || "";
  if (v >= 1e12) return `${sym}${fmt(v / 1e12, 1)}T`;
  if (v >= 1e9) return `${sym}${fmt(v / 1e9, 1)}B`;
  return `${sym}${fmt(v, 0)}`;
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// 1 ช่องในตาราง: ค่าปกติ / ดึงไม่สำเร็จ / ยังไม่มีแหล่ง / ข้อมูลเก่า
function cell(f, kind) {
  if (!f || f.value == null) {
    if (f && f.todo) return `<td class="num"><span class="todo" title="${esc(f.error)}">–</span></td>`;
    return `<td class="num"><span class="fail" title="${esc(f && f.error)}">ดึงไม่สำเร็จ</span></td>`;
  }
  const text = kind === "cap" ? fmtCap(f.value, f.currency) : fmt(f.value);
  const tip = [f.asof && "ข้อมูล ณ " + thaiDate(f.asof), f.note, f.source].filter(Boolean).join(" · ");
  const stale = f.stale ? ` <span class="stale" title="ข้อมูลเก่า – รอบล่าสุดดึงไม่สำเร็จ">⚠</span>` : "";
  return `<td class="num" title="${esc(tip)}">${text}${stale}</td>`;
}

function rowHTML(x) {
  const L = x.level || {};
  const date = L.value != null ? esc(thaiDateShort(L.asof)) : "–";
  return `<tr>
    <td class="name">${TV[x.id]
      ? `<a class="tv" href="${tvLink(x.id)}" target="_blank" rel="noopener" title="ดูกราฟใน TradingView">${esc(SHORT[x.id] || x.name)} <span class="tv-ico">↗</span></a>`
      : esc(SHORT[x.id] || x.name)}</td>
    ${cell(L, "level")}
    ${cell(x.market_cap, "cap")}
    ${cell(x.pe, "x")}
    ${cell(x.pbv, "x")}
    <td class="date">${date}</td>
  </tr>`;
}

// รายละเอียดแหล่งข้อมูล/สาเหตุที่ดึงไม่สำเร็จ (ซ่อนไว้ กดเปิดได้)
function detailsHTML(list) {
  const lines = [];
  const lab = { level: "ระดับดัชนี", market_cap: "Market Cap", pe: "P/E", pbv: "P/BV" };
  for (const x of list) {
    for (const k of Object.keys(lab)) {
      const f = x[k] || {};
      const name = `${SHORT[x.id] || x.name} – ${lab[k]}`;
      if (f.value == null) lines.push(`<li><b>${esc(name)}:</b> <span class="${f.todo ? "todo" : "fail-text"}">${esc(f.error || "ไม่มีข้อมูล")}</span></li>`);
      else lines.push(`<li><b>${esc(name)}:</b> ${esc([f.asof && thaiDate(f.asof), f.note, f.source].filter(Boolean).join(" · "))}${f.stale ? ' <span class="stale">⚠ ข้อมูลเก่า</span>' : ""}</li>`);
    }
  }
  return `<details class="details"><summary>แหล่งข้อมูล / สาเหตุที่ดึงไม่สำเร็จ</summary><ul>${lines.join("")}</ul></details>`;
}

// ---------------- หน้า 1: ดัชนีสำคัญ ----------------
async function loadIndices() {
  const grid = document.getElementById("indices-grid");
  const upd = document.getElementById("indices-updated");
  try {
    const r = await fetch("data/indices.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    upd.textContent = "อัปเดตล่าสุด: " + thaiDateTime(data.updated_at) + " (เวลาไทย)";
    try { renderVIX(data.vix); } catch (e) { console.error(e); }
    try { renderSoxx(data.soxx_spx); } catch (e) { console.error(e); }
    grid.innerHTML = `
      <table class="idx-table">
        <thead><tr>
          <th>ดัชนี</th><th class="num">ระดับ (จุด)</th><th class="num">Market Cap</th>
          <th class="num">P/E</th><th class="num">P/BV</th><th>ข้อมูล ณ</th>
        </tr></thead>
        <tbody>${data.indices.map(rowHTML).join("")}</tbody>
      </table>
      <p class="legend">แตะชื่อดัชนีเพื่อดูกราฟใน TradingView · <span class="fail">ดึงไม่สำเร็จ</span> = ดึงข้อมูลไม่สำเร็จ · – = ยังไม่มีแหล่งข้อมูล · ⚠ = ข้อมูลเก่า · T = ล้านล้าน, B = พันล้าน</p>
      ${detailsHTML(data.indices)}`;
  } catch (e) {
    upd.innerHTML = `<span class="fail">ดึงข้อมูลไม่สำเร็จ</span> โหลดไฟล์ข้อมูลดัชนีไม่ได้ (${esc(e.message)})`;
  }
}

loadIndices();

// ---------------- หน้า 2: อเมริกา ----------------
const pct = (v) => (v == null ? "–" : `${Number(v).toFixed(2)}%`);
const pct1 = (v) => (v == null ? "–" : `${Number(v).toFixed(1)}%`);

function thaiMonth(ym) {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("th-TH", { month: "short", year: "numeric" });
}

function sectionShell(title, sub, bodyHTML, sec) {
  const stale = sec && sec.stale
    ? `<p class="stale">⚠ ข้อมูลเก่า – รอบล่าสุดดึงไม่สำเร็จ (${esc(sec.error)})</p>` : "";
  const btn = sec && sec.link
    ? `<a class="btn" href="${esc(sec.link)}" target="_blank" rel="noopener">ดูข้อมูล ↗</a>` : "";
  const src = sec && sec.source ? `<span class="src">ที่มา: ${esc(sec.source)}</span>` : "";
  return `<h2>${title}</h2>${sub ? `<p class="panel-sub">${sub}</p>` : ""}${stale}${bodyHTML}
    <div class="panel-foot">${btn}${src}</div>`;
}

function failHTML(title, sec) {
  return `<h2>${title}</h2><p><span class="fail">ดึงข้อมูลไม่สำเร็จ</span> <span class="small">${esc(sec && sec.error)}</span></p>`;
}

function nextRelHTML(rel) {
  if (!rel || !rel.items || !rel.items.length) return "";
  const r = rel.items[0];
  return `<p class="next-rel">📅 ประกาศครั้งถัดไป: <b>${esc(thaiDate(r.thai_date))} เวลา ${esc(r.thai_time)} น.</b> (ไทย) · ${esc(r.title)}</p>`;
}

function renderGDP(sec, rel) {
  const el = document.getElementById("us-gdp");
  const title = "GDP สหรัฐฯ";
  if (!sec || !sec.rows) { el.innerHTML = failHTML(title, sec); return; }
  const rows = sec.rows.map((r, i) => `
    <tr class="${i === 0 ? "latest" : ""}">
      <td>${esc(r.quarter)}${i === 0 ? ' <span class="badge">ล่าสุด</span>' : ""}</td>
      <td class="num ${r.growth > 0 ? "up" : r.growth < 0 ? "down" : ""}">${pct1(r.growth)}</td>
      <td class="num">${r.size_bn == null ? "–" : "$" + fmt(r.size_bn / 1000, 2) + "T"}</td>
    </tr>`).join("");
  el.innerHTML = sectionShell(title,
    "GDP Growth = Real GDP % QoQ (ปรับเป็นอัตรารายปี) · ขนาด GDP = มูลค่า ณ ราคาปัจจุบัน (ปรับเป็นรายปี) · T = ล้านล้านดอลลาร์",
    nextRelHTML(rel) + `<table class="idx-table"><thead><tr><th>ไตรมาส</th><th class="num">GDP Growth (QoQ)</th><th class="num">ขนาด GDP</th></tr></thead><tbody>${rows}</tbody></table>`,
    sec);
}

function renderFed(sec) {
  const el = document.getElementById("us-fed");
  const title = "ตารางประชุมเฟด (FOMC)";
  if (!sec || !sec.meetings) { el.innerHTML = failHTML(title, sec); return; }
  const list = [...sec.meetings].reverse(); // ล่าสุดอยู่บน เหมือนในเว็บ investing
  const rows = list.map((m) => {
    let actual = "", cls = "";
    if (m.actual != null) {
      const d = m.actual - m.previous;
      cls = d > 0 ? "up" : d < 0 ? "down" : "";
      const arrow = d > 0 ? " ▲" : d < 0 ? " ▼" : "";
      actual = `<span title="${m.actual_range ? m.actual_range.map(pct).join(" – ") : ""}">${pct(m.actual)}${arrow}</span>`;
    } else if (m.status === "waiting") {
      actual = `<span class="small">รอข้อมูล</span>`;
    }
    const badge = m.next ? ' <span class="badge">ครั้งถัดไป</span>' : "";
    return `<tr class="${m.next ? "latest" : ""} ${m.status === "upcoming" && !m.next ? "muted" : ""}">
      <td>${esc(thaiDate(m.thai_date))}${badge}</td>
      <td>${esc(m.thai_time)} น.</td>
      <td class="num ${cls}">${actual}</td>
      <td class="num" title="${m.previous_range ? m.previous_range.map(pct).join(" – ") : ""}">${pct(m.previous)}</td>
    </tr>`;
  }).join("");
  const cur = sec.current_range ? `ดอกเบี้ยนโยบายปัจจุบัน <b>${pct(sec.current_range[0])} – ${pct(sec.current_range[1])}</b> · ` : "";
  el.innerHTML = sectionShell(`${title} ปี ${sec.year}`,
    `${cur}ตัวเลขในตารางคือกรอบบนของดอกเบี้ย · วันเวลาเป็นเวลาไทย (เวลาแถลงผล)`,
    `<table class="idx-table"><thead><tr><th>วันที่ (ไทย)</th><th>เวลา</th><th class="num">ผล</th><th class="num">ก่อนหน้า</th></tr></thead><tbody>${rows}</tbody></table>`,
    sec);
}

function renderCPI(sec, rel) {
  const el = document.getElementById("us-cpi");
  const title = "เงินเฟ้อ CPI สหรัฐฯ (YoY)";
  if (!sec || !sec.rows) { el.innerHTML = failHTML(title, sec); return; }
  const rows = sec.rows.map((r, i) => `
    <tr class="${i === 0 ? "latest" : ""}">
      <td>${esc(thaiMonth(r.month))}${i === 0 ? ' <span class="badge">ล่าสุด</span>' : ""}</td>
      <td class="num">${r.yoy == null ? `<span class="todo" title="${esc(r.note)}">– *</span>` : pct1(r.yoy)}</td>
    </tr>`).join("");
  const notes = sec.rows.filter((r) => r.yoy == null && r.note)
    .map((r) => `<p class="small">* ${esc(thaiMonth(r.month))}: ${esc(r.note)} – ดูตัวเลขที่ทางการประกาศได้จากปุ่ม "ดูข้อมูล"</p>`).join("");
  el.innerHTML = sectionShell(title, "Headline CPI เทียบเดือนเดียวกันปีก่อน (ประกาศทุกเดือน)",
    nextRelHTML(rel) + `<table class="idx-table"><thead><tr><th>เดือน</th><th class="num">CPI YoY</th></tr></thead><tbody>${rows}</tbody></table>${notes}`,
    sec);
}

async function loadUS() {
  const upd = document.getElementById("us-updated");
  try {
    const r = await fetch("data/us.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const d = await r.json();
    upd.textContent = "อัปเดตล่าสุด: " + thaiDateTime(d.updated_at) + " (เวลาไทย)";
    // แต่ละกล่องแยกกัน กล่องไหนพังไม่กระทบกล่องอื่น
    const rel = d.releases || {};
    for (const [fn, sec, r] of [[renderGDP, d.gdp, rel.gdp], [renderFed, d.fed], [renderCPI, d.cpi, rel.cpi]]) {
      try { fn(sec, r); } catch (e) { console.error(e); }
    }
    try { renderExtra(d.extra); } catch (e) { console.error(e); }
  } catch (e) {
    upd.innerHTML = `<span class="fail">ดึงข้อมูลไม่สำเร็จ</span> โหลดไฟล์ข้อมูลอเมริกาไม่ได้ (${esc(e.message)})`;
  }
}


// ============================================================
// กราฟ (SVG ทำเอง ไม่ต้องโหลดไลบรารีเพิ่ม) - แกนนอน = เวลา, แกนตั้ง = ค่า
// ============================================================
const CHARTS = {}; // เก็บไว้วาดใหม่ตอนหมุนจอ/ปรับขนาดหน้าต่าง (key = id ของกล่องกราฟ)

function niceTicks(min, max, count) {
  const span = max - min || 1;
  const raw = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= count) || 10 * mag;
  const out = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}

function drawChart(box, opt) {
  const W = Math.max(280, box.clientWidth || 320);
  const H = opt.height || 200;
  const M = { l: opt.left || 48, r: 12, t: 10, b: 26 };
  const pw = W - M.l - M.r, ph = H - M.t - M.b;
  const all = opt.series.flatMap((s) => s.data.filter((p) => p[1] != null));
  if (!all.length) { box.innerHTML = '<p class="small">ไม่มีข้อมูล</p>'; return; }
  const tx = (d) => new Date(d + "T00:00:00").getTime();
  let x0 = Math.min(...all.map((p) => tx(p[0]))), x1 = Math.max(...all.map((p) => tx(p[0])));
  if (x0 === x1) x1 = x0 + 864e5;
  let y0 = Math.min(...all.map((p) => p[1])), y1 = Math.max(...all.map((p) => p[1]));
  if (opt.zero || opt.series.some((s) => s.type === "bar")) { y0 = Math.min(0, y0); y1 = Math.max(0, y1); }
  for (const v of opt.yInclude || []) { y0 = Math.min(y0, v); y1 = Math.max(y1, v); }
  const pad = (y1 - y0) * 0.08 || Math.abs(y1) * 0.05 || 1;
  y0 -= opt.zero && y0 === 0 ? 0 : pad; y1 += pad;
  const X = (t) => M.l + ((t - x0) / (x1 - x0)) * pw;
  const Y = (v) => M.t + (1 - (v - y0) / (y1 - y0)) * ph;
  const fmtY = opt.yFmt || ((v) => fmt(v, 1));

  let svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="chart-svg">`;
  // พื้นหลังแบ่งโซน (เช่น VIX: โลภ / ปกติ / กลัว)
  for (const b of opt.bands || []) {
    const top = Y(Math.min(b.to, y1)), bot = Y(Math.max(b.from, y0));
    if (bot > top) svg += `<rect x="${M.l}" y="${top}" width="${pw}" height="${bot - top}" fill="${b.color}" opacity="${b.opacity || 0.13}"/>`;
    if (b.label && bot - top > 16) svg += `<text x="${M.l + 6}" y="${top + 15}" class="band-label" fill="${b.text || b.color}">${b.label}</text>`;
  }
  for (const v of niceTicks(y0, y1, 4)) {
    svg += `<line x1="${M.l}" x2="${W - M.r}" y1="${Y(v)}" y2="${Y(v)}" class="grid"/>`;
    svg += `<text x="${M.l - 6}" y="${Y(v) + 4}" class="ytick">${fmtY(v)}</text>`;
  }
  if (y0 < 0 && y1 > 0) svg += `<line x1="${M.l}" x2="${W - M.r}" y1="${Y(0)}" y2="${Y(0)}" class="zero"/>`;
  for (const l of opt.hlines || []) {
    svg += `<line x1="${M.l}" x2="${W - M.r}" y1="${Y(l.y)}" y2="${Y(l.y)}" stroke="${l.color}" stroke-width="1.5" stroke-dasharray="6 4"/>`;
    svg += `<text x="${W - M.r - 16}" y="${Y(l.y) - 5}" class="hline-label" fill="${l.color}">${l.label || l.y}</text>`;
  }
  // แกนเวลา: ป้ายเดือน/ปี ประมาณ 4-6 จุด
  const months = Math.max(1, Math.round((x1 - x0) / (30.4 * 864e5)));
  const every = [1, 2, 3, 4, 6, 12, 24].find((e) => months / e <= (W < 420 ? 4 : 6)) || 24;
  const d = new Date(x0); d.setDate(1); d.setMonth(d.getMonth() + 1);
  while (d.getTime() <= x1) {
    if (d.getMonth() % every === 0 || every === 1) {
      const lbl = d.toLocaleDateString("th-TH", { month: "short", year: "2-digit" });
      svg += `<text x="${X(d.getTime())}" y="${H - 6}" class="xtick">${lbl}</text>`;
      svg += `<line x1="${X(d.getTime())}" x2="${X(d.getTime())}" y1="${M.t}" y2="${M.t + ph}" class="grid vgrid"/>`;
    }
    d.setMonth(d.getMonth() + 1);
  }
  for (const s of opt.series) {
    const pts = s.data.filter((p) => p[1] != null);
    if (s.type === "bar") {
      const bw = Math.max(2, (pw / s.data.length) * 0.65);
      for (const p of pts) {
        const x = X(tx(p[0])), y = Y(p[1]);
        svg += `<rect x="${x - bw / 2}" y="${Math.min(y, Y(0))}" width="${bw}" height="${Math.abs(Y(0) - y)}" fill="${p[1] >= 0 ? (s.color || "var(--up)") : "var(--down)"}" rx="1"/>`;
      }
      continue;
    }
    // เส้น (step = เส้นแบบขั้นบันได ใช้กับเพดานหนี้) / ช่วงที่ไม่มีค่า (null) จะเว้นว่าง
    let path = "", prev = null;
    for (const p of s.data) {
      if (p[1] == null) { prev = null; continue; }
      const x = X(tx(p[0])), y = Y(p[1]);
      if (!prev) path += `M${x},${y}`;
      else path += s.type === "step" ? `H${x}V${y}` : `L${x},${y}`;
      prev = p;
    }
    svg += `<path d="${path}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2}" ${s.dash ? 'stroke-dasharray="6 4"' : ""} stroke-linejoin="round"/>`;
    const last = pts[pts.length - 1];
    if (last && !s.noDot) svg += `<circle cx="${X(tx(last[0]))}" cy="${Y(last[1])}" r="3.5" fill="${s.color}"/>`;
  }
  svg += `<line class="hover-line" x1="0" x2="0" y1="${M.t}" y2="${M.t + ph}" style="display:none"/>`;
  svg += `<rect x="${M.l}" y="${M.t}" width="${pw}" height="${ph}" fill="transparent" class="hit"/></svg>`;
  box.innerHTML = `<div class="chart-wrap">${svg}<div class="chart-tip" style="display:none"></div></div>`;

  // แตะ/ชี้บนกราฟ -> โชว์ค่าของวันนั้น
  const wrap = box.firstChild, tip = wrap.querySelector(".chart-tip"), vline = wrap.querySelector(".hover-line");
  const base = opt.series[0].data;
  const show = (ev) => {
    const r = wrap.getBoundingClientRect();
    const cx = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
    const t = x0 + ((cx - M.l) / pw) * (x1 - x0);
    let best = base[0];
    for (const p of base) if (Math.abs(tx(p[0]) - t) < Math.abs(tx(best[0]) - t)) best = p;
    const vals = opt.series.map((s) => {
      const p = s.data.find((q) => q[0] === best[0]) || s.data.reduce((a, q) => (Math.abs(tx(q[0]) - tx(best[0])) < Math.abs(tx(a[0]) - tx(best[0])) ? q : a), s.data[0]);
      return `<span style="color:${s.color || "var(--text)"}">${esc(s.label || "")} ${p && p[1] != null ? (opt.tipFmt || fmtY)(p[1]) : "–"}</span>`;
    });
    const x = X(tx(best[0]));
    vline.setAttribute("x1", x); vline.setAttribute("x2", x); vline.style.display = "";
    tip.innerHTML = `<b>${esc((opt.tipDate || thaiDate)(best[0]))}</b><br>${vals.join("<br>")}`;
    tip.style.display = "";
    tip.style.left = Math.min(Math.max(0, x - 70), W - 150) + "px";
  };
  const hide = () => { tip.style.display = "none"; vline.style.display = "none"; };
  const hit = wrap.querySelector(".hit");
  hit.addEventListener("mousemove", show); hit.addEventListener("mouseleave", hide);
  hit.addEventListener("touchstart", show, { passive: true }); hit.addEventListener("touchmove", show, { passive: true });
  hit.addEventListener("touchend", () => setTimeout(hide, 2500));
}

function chartBox(id, opt) {
  const box = document.getElementById(id);
  if (!box) return;
  const render = () => drawChart(box, opt);
  CHARTS[id] = render;
  render();
}

let _rz;
window.addEventListener("resize", () => { clearTimeout(_rz); _rz = setTimeout(() => Object.values(CHARTS).forEach((f) => f()), 200); });

function legendHTML(items) {
  return `<div class="legend-row">${items.map(([c, t, dash]) => `<span><i style="background:${dash ? "transparent" : c};border-top:${dash ? `2px dashed ${c}` : "none"}"></i>${t}</span>`).join("")}</div>`;
}

function infoHTML(sec, asof, asofText) {
  return `<p class="update-info">📅 ข้อมูล${asofText ? "" : " ณ"} <b>${esc(asofText || thaiDate(asof))}</b> · ปรับปรุง: ${esc(sec.freq)}<br>
    ⏭ รอบถัดไปประมาณ <b>${esc(thaiDate(sec.next))}</b></p>`;
}

function extraPanel(id, title, sec, bodyFn) {
  const el = document.getElementById(id);
  if (!sec || !sec.ok) { el.innerHTML = failHTML(title, sec); return; }
  el.innerHTML = sectionShell(title, "", bodyFn(), sec);
}

const C = { blue: "#5aa9ff", gold: "#ffd479", green: "#2fbf71", red: "#f0566a", purple: "#b48cff", gray: "#8b98a8" };
const sgn = (v, d = 2) => (v > 0 ? "+" : "") + fmt(v, d);

function renderExtra(x) {
  if (!x) return;

  extraPanel("us-dxy", "Dollar Index (DXY)", x.dxy, () => {
    const L = x.dxy.latest, s = x.dxy.dxy, first = s[0][1];
    return `<p class="big-num">${fmt(L.value, 2)} <span class="small">(${sgn((L.value / first - 1) * 100, 1)}% ใน 2 ปี)</span></p>
      <p class="panel-sub">ค่าเงินดอลลาร์เทียบ 6 สกุลหลัก · ดอลลาร์แข็ง (กราฟขึ้น) มักกดดันเงินบาทและเงินทุนไหลออกจากตลาดเกิดใหม่</p>
      <div id="ch-dxy"></div>${infoHTML(x.dxy, L.date)}`;
  });
  if (x.dxy && x.dxy.ok) chartBox("ch-dxy", { series: [{ data: x.dxy.dxy, color: C.gold, label: "DXY" }], yFmt: (v) => fmt(v, 0), tipFmt: (v) => fmt(v, 2) });

  extraPanel("us-yields", "อัตราผลตอบแทนพันธบัตรรัฐบาลสหรัฐฯ", x.yields, () => {
    const L = x.yields.latest;
    return `<p class="big-num">10 ปี ${pct(L.y10)} · 2 ปี ${pct(L.y2)}</p>
      <p class="panel-sub">ส่วนต่าง 10 ปี − 2 ปี = <b class="${L.spread < 0 ? "neg" : ""}">${sgn(L.spread)}%</b> · ถ้าติดลบ (yield curve กลับหัว) มักเป็นสัญญาณเตือนเศรษฐกิจถดถอย</p>
      ${legendHTML([[C.blue, "10 ปี"], [C.purple, "2 ปี"]])}<div id="ch-yields"></div>
      ${legendHTML([[C.gold, "ส่วนต่าง 10 ปี − 2 ปี"]])}<div id="ch-spread"></div>${infoHTML(x.yields, L.date)}`;
  });
  if (x.yields && x.yields.ok) {
    chartBox("ch-yields", { series: [{ data: x.yields.y10, color: C.blue, label: "10 ปี" }, { data: x.yields.y2, color: C.purple, label: "2 ปี" }], yFmt: (v) => fmt(v, 1) + "%", tipFmt: (v) => fmt(v, 2) + "%" });
    chartBox("ch-spread", { height: 130, zero: true, series: [{ data: x.yields.spread, color: C.gold, label: "ส่วนต่าง", width: 1.6 }], yFmt: (v) => fmt(v, 1), tipFmt: (v) => sgn(v) + "%" });
  }

  extraPanel("us-nfp", "การจ้างงานนอกภาคเกษตร (NFP) + อัตราว่างงาน", x.nfp, () => {
    const L = x.nfp.latest;
    return `<p class="big-num">${sgn(L.nfp, 0)}K ตำแหน่ง <span class="small">(${esc(thaiMonth(L.month))})</span></p>
      <p class="panel-sub">จำนวนงานที่เพิ่ม/ลดในเดือนนั้น (พันตำแหน่ง) · อัตราว่างงานล่าสุด <b>${fmt(L.unrate, 1)}%</b> · เฟดใช้ดูตลาดแรงงานคู่กับเงินเฟ้อ</p>
      ${legendHTML([[C.green, "งานเพิ่ม/ลดต่อเดือน (พันตำแหน่ง)"]])}<div id="ch-nfp"></div>
      ${legendHTML([[C.red, "อัตราว่างงาน (%)"]])}<div id="ch-unrate"></div>${infoHTML(x.nfp, null, "เดือน " + thaiMonth(L.month))}`;
  });
  if (x.nfp && x.nfp.ok) {
    chartBox("ch-nfp", { series: [{ data: x.nfp.nfp, color: C.green, type: "bar", label: "NFP" }], yFmt: (v) => fmt(v, 0), tipFmt: (v) => sgn(v, 0) + "K" });
    chartBox("ch-unrate", { height: 130, series: [{ data: x.nfp.unrate, color: C.red, label: "ว่างงาน" }], yFmt: (v) => fmt(v, 1) + "%", tipFmt: (v) => fmt(v, 1) + "%" });
  }

  extraPanel("us-fedbs", "งบดุลเฟด (Fed Balance Sheet)", x.fedbs, () => {
    const L = x.fedbs.latest, s = x.fedbs.walcl, first = s[0][1];
    return `<p class="big-num">$${fmt(L.value, 2)}T <span class="small">(${sgn(L.value - first, 2)}T ใน 2 ปี)</span></p>
      <p class="panel-sub">สินทรัพย์รวมของเฟด · เส้นลง = เฟดดูดสภาพคล่องออก (QT) · เส้นขึ้น = อัดสภาพคล่องเข้าระบบ (QE) · T = ล้านล้านดอลลาร์</p>
      <div id="ch-fedbs"></div>${infoHTML(x.fedbs, L.date)}`;
  });
  if (x.fedbs && x.fedbs.ok) chartBox("ch-fedbs", { series: [{ data: x.fedbs.walcl, color: C.blue, label: "งบดุล" }], yFmt: (v) => "$" + fmt(v, 1) + "T", tipFmt: (v) => "$" + fmt(v, 3) + "T" });

  extraPanel("us-debt", "หนี้รัฐบาลกลางสหรัฐฯ + เพดานหนี้", x.debt, () => {
    const L = x.debt.latest;
    const room = L.limit ? L.limit - (L.subject || L.debt) : null;
    return `<p class="big-num">$${fmt(L.debt, 2)}T <span class="small">เพดาน $${L.limit ? fmt(L.limit, 2) + "T" : "–"}</span></p>
      <p class="panel-sub">${room != null ? `เหลือช่องว่างก่อนชนเพดานประมาณ <b>$${fmt(room, 2)}T</b> ${L.subject ? "(คิดจากหนี้ที่นับรวมเพดาน)" : ""} · ` : ""}ช่วงที่เส้นเพดานหายไป = สภาฯ ระงับเพดานหนี้ชั่วคราว · ย้อนหลัง 5 ปี</p>
      ${legendHTML([[C.gold, "หนี้รวม"], [C.red, "เพดานหนี้", true]])}<div id="ch-debt"></div>${infoHTML(x.debt, L.date)}`;
  });
  if (x.debt && x.debt.ok) chartBox("ch-debt", { height: 220, series: [{ data: x.debt.debt, color: C.gold, label: "หนี้" }, { data: x.debt.limit, color: C.red, type: "step", dash: true, label: "เพดาน", noDot: true }], yFmt: (v) => "$" + fmt(v, 0) + "T", tipFmt: (v) => "$" + fmt(v, 2) + "T" });
}

loadUS();

// ---------------- หน้า 3: ไทย ----------------
function renderThGDP(sec) {
  const el = document.getElementById("th-gdp");
  const title = "GDP ไทย";
  if (!sec || !sec.rows) { el.innerHTML = failHTML(title, sec); return; }
  const rows = sec.rows.map((r, i) => `
    <tr class="${i === 0 ? "latest" : ""}">
      <td>Q${r.q}/${r.year + 543}${i === 0 ? ' <span class="badge">ล่าสุด</span>' : ""}</td>
      <td class="num ${r.growth > 0 ? "up" : r.growth < 0 ? "down" : ""}">${pct1(r.growth)}</td>
      <td class="num">${pct1(r.yoy)}</td>
      <td class="num">${r.size_mb == null ? "–" : "฿" + fmt(r.size_mb / 1e6, 2) + "T"}</td>
    </tr>`).join("");
  const rel = sec.release_date ? ` · สศช. เผยแพร่ ${esc(thaiDate(sec.release_date))}` : "";
  el.innerHTML = sectionShell(title,
    `QoQ = เทียบไตรมาสก่อน (ปรับฤดูกาล) · YoY = เทียบไตรมาสเดียวกันปีก่อน · ขนาด GDP = มูลค่า ณ ราคาประจำปีของไตรมาสนั้น (T = ล้านล้านบาท)${rel}`,
    `<table class="idx-table"><thead><tr><th>ไตรมาส</th><th class="num">QoQ (SA)</th><th class="num">YoY</th><th class="num">ขนาด GDP</th></tr></thead><tbody>${rows}</tbody></table>`,
    sec);
}

function renderThMPC(sec) {
  const el = document.getElementById("th-mpc");
  const title = "ตารางประชุม กนง.";
  if (!sec || !sec.meetings) { el.innerHTML = failHTML(title, sec); return; }
  const list = [...sec.meetings].reverse();
  const rows = list.map((m) => {
    let actual = "", cls = "";
    if (m.actual != null) {
      const d = m.actual - m.previous;
      cls = d > 0 ? "up" : d < 0 ? "down" : "";
      actual = `${pct(m.actual)}${d > 0 ? " ▲" : d < 0 ? " ▼" : ""}`;
    } else if (m.status === "waiting") {
      actual = `<span class="small">รอข้อมูล</span>`;
    }
    const badge = m.next ? ' <span class="badge">ครั้งถัดไป</span>' : "";
    return `<tr class="${m.next ? "latest" : ""} ${m.status === "upcoming" && !m.next ? "muted" : ""}">
      <td>${esc(thaiDate(m.thai_date))}${badge}</td>
      <td class="small">${esc(m.decision || "")}</td>
      <td class="num ${cls}">${actual}</td>
      <td class="num">${pct(m.previous)}</td>
    </tr>`;
  }).join("");
  el.innerHTML = sectionShell(`${title} ปี ${sec.year + 543}`,
    `ดอกเบี้ยนโยบายปัจจุบัน <b>${pct(sec.current)}</b> · แถลงผลเวลา 14:00 น.`,
    `<table class="idx-table"><thead><tr><th>วันที่แถลงผล</th><th>มติ</th><th class="num">ผล</th><th class="num">ก่อนหน้า</th></tr></thead><tbody>${rows}</tbody></table>`,
    sec);
}

function renderThCPI(sec) {
  const el = document.getElementById("th-cpi");
  const title = "เงินเฟ้อไทย (CPI ทั่วไป)";
  if (!sec || !sec.rows) { el.innerHTML = failHTML(title, sec); return; }
  const rows = sec.rows.map((r, i) => `
    <tr class="${i === 0 ? "latest" : ""}">
      <td>${esc(thaiMonth(r.month))}${i === 0 ? ' <span class="badge">ล่าสุด</span>' : ""}</td>
      <td class="num">${pct(r.yoy)}</td>
      <td class="num">${r.mom == null ? "–" : pct(r.mom)}</td>
    </tr>`).join("");
  const upd = sec.last_updated ? `อัปเดตโดย สนค. ${esc(thaiDateTime(sec.last_updated))}` : "";
  el.innerHTML = sectionShell(title, `เงินเฟ้อทั่วไป เทียบเดือนเดียวกันปีก่อน (YoY) และเทียบเดือนก่อน (MoM) · ${upd}`,
    `<table class="idx-table"><thead><tr><th>เดือน</th><th class="num">YoY</th><th class="num">MoM</th></tr></thead><tbody>${rows}</tbody></table>`,
    sec);
}

function renderThExport(sec) {
  const el = document.getElementById("th-export");
  const title = "การส่งออกไทย";
  if (!sec || !sec.rows) { el.innerHTML = failHTML(title, sec); return; }
  const rows = sec.rows.map((r, i) => `
    <tr class="${i === 0 ? "latest" : ""}">
      <td>${esc(thaiMonth(r.month))}${i === 0 ? ' <span class="badge">ล่าสุด</span>' : ""}</td>
      <td class="num">${fmt(r.usd_mn, 0)}</td>
      <td class="num ${r.yoy > 0 ? "up" : r.yoy < 0 ? "down" : ""}">${r.yoy == null ? "–" : (r.yoy > 0 ? "+" : "") + pct1(r.yoy)}</td>
      <td class="num">${fmt(r.baht_mn / 1000, 1)}</td>
    </tr>`).join("");
  const r0 = sec.rows[0];
  const ytd = r0 && r0.ytd_yoy != null ? ` · สะสมตั้งแต่ต้นปีถึง ${esc(thaiMonth(r0.month))}: <b>${r0.ytd_yoy > 0 ? "+" : ""}${pct1(r0.ytd_yoy)}</b>` : "";
  el.innerHTML = sectionShell(title,
    `มูลค่าส่งออกรายเดือน · YoY คิดจากดอลลาร์ (แบบที่กระทรวงพาณิชย์แถลง)${ytd}`,
    `<table class="idx-table"><thead><tr><th>เดือน</th><th class="num">ล้าน USD</th><th class="num">YoY</th><th class="num">พันล้านบาท</th></tr></thead><tbody>${rows}</tbody></table>`,
    sec);
}

const INV_NAME = { institution: "สถาบันในประเทศ", proprietary: "บัญชีบริษัทหลักทรัพย์", foreign: "นักลงทุนต่างประเทศ", individual: "นักลงทุนรายย่อยในประเทศ" };
const netCell = (v) => `<td class="num ${v > 0 ? "up" : v < 0 ? "down" : ""}">${v == null ? "–" : (v > 0 ? "+" : "") + fmt(v, 0)}</td>`;

function renderThInvestor(sec) {
  const el = document.getElementById("th-investor");
  const title = "มูลค่าซื้อขายตามกลุ่มนักลงทุน (SET)";
  if (!sec || !sec.mtd) { el.innerHTML = failHTML(title, sec); return; }
  const prev = sec.prev_month || null;
  const mtd = Object.fromEntries(sec.mtd.rows.map((r) => [r.type, r]));
  const ytd = Object.fromEntries(sec.ytd.rows.map((r) => [r.type, r]));
  const types = sec.mtd.rows.map((r) => r.type);
  const range = (b) => `${thaiDateShort(b.begin)} – ${thaiDateShort(b.end)}`;
  const t1 = types.map((t) => `<tr><td class="inv-name">${INV_NAME[t] || t}</td>
      ${prev ? netCell(prev.net[t]) : ""}${netCell(mtd[t].net)}${netCell(ytd[t].net)}</tr>`).join("");
  const t2 = types.map((t) => `<tr><td class="inv-name">${INV_NAME[t] || t}</td>
      <td class="num">${fmt(mtd[t].buy, 0)}</td><td class="num">${fmt(mtd[t].sell, 0)}</td>${netCell(mtd[t].net)}</tr>`).join("");
  el.innerHTML = sectionShell(title, "ซื้อ/ขายสุทธิ หน่วย: ล้านบาท · สีเขียว = ซื้อสุทธิ · สีแดง = ขายสุทธิ", `
    <table class="idx-table inv-table"><thead><tr><th>กลุ่ม</th>
      ${prev ? `<th class="num">${esc(thaiMonth(prev.month))}<br><span class="th-sub">ปิดเดือน</span></th>` : ""}
      <th class="num">เดือนนี้<br><span class="th-sub">${esc(range(sec.mtd))}</span></th>
      <th class="num">ตั้งแต่ต้นปี<br><span class="th-sub">ถึง ${esc(thaiDateShort(sec.ytd.end))}</span></th></tr></thead><tbody>${t1}</tbody></table>
    <p class="panel-sub" style="margin-top:12px !important">รายละเอียดเดือนนี้ (${esc(range(sec.mtd))})</p>
    <table class="idx-table inv-table"><thead><tr><th>กลุ่ม</th><th class="num">ซื้อ</th><th class="num">ขาย</th><th class="num">สุทธิ</th></tr></thead><tbody>${t2}</tbody></table>
    ${sec.remark ? `<p class="small" style="margin-top:8px">หมายเหตุ: ${esc(sec.remark.replace(/\s*คลิกที่นี่\s*\.?$/, ""))}</p>` : ""}
    <p class="update-info">📅 ข้อมูล ณ <b>${esc(thaiDate(sec.mtd.end))}</b> · ปรับปรุงทุกวันทำการ (บอทดึงทุก 6 ชั่วโมง)</p>`, sec);
}

function renderThMSCI(d) {
  const el = document.getElementById("th-msci");
  const title = "MSCI ปรับเพิ่ม/ลดหุ้นไทย";
  if (!d) { el.innerHTML = failHTML(title, { error: "โหลดข้อมูลไม่ได้" }); return; }
  const L = d.latest, N = d.next;
  const list = (arr) => (arr && arr.length ? arr.map((x) => `<li>${esc(x)}</li>`).join("") : `<li class="small">ไม่มี</li>`);
  let body = "";
  if (L && L.ok) {
    const sec = (key, label) => {
      const s = L[key] || {};
      return `<div class="msci-sec"><p class="msci-h">${label}</p>
        <div class="msci-cols"><div><p class="up">➕ เพิ่มเข้า</p><ul>${list(s.add)}</ul></div>
        <div><p class="down">➖ ถูกคัดออก</p><ul>${list(s.delete)}</ul></div></div></div>`;
    };
    body = `<p class="big-num" style="font-size:20px">รอบ ${esc(L.review)} ${L.manual ? '<span class="small">(ข้อมูลใส่โดย Claude)</span>' : ""}</p>
      <p class="panel-sub">ประกาศ ${esc(thaiDateTime(L.announce_thai))} · ปรับพอร์ตจริงตอนปิดตลาด <b>${esc(thaiDate(L.trade_close))}</b></p>
      ${sec("standard", "MSCI Thailand (ดัชนีหลัก)")}${sec("smallcap", "MSCI Thailand Small Cap (หุ้นขนาดเล็ก)")}`;
  } else if (L) {
    body = `<div class="msci-warn">⚠️ MSCI ประกาศผลรอบ <b>${esc(L.review)}</b> แล้ว (${esc(thaiDateTime(L.announce_thai))})
      แต่บอทดึงรายชื่อหุ้นอัตโนมัติไม่สำเร็จ<br><br>👉 <b>บอก Claude ว่า "MSCI ปรับรายชื่อหุ้นรอบ ${esc(L.review)} แล้ว ช่วยดึงข้อมูลมาแสดงให้หน่อย"</b></div>`;
  }
  const nextTxt = N ? `<p class="update-info">⏭ รอบถัดไป: <b>${esc(N.review)}</b> · ประกาศ ${esc(thaiDateTime(N.announce_thai))} · ปรับพอร์ตจริงปิดตลาด ${esc(thaiDate(N.trade_close))}<br>
    🔔 แจ้งเตือน ntfy: วันที่ MSCI จะประกาศ และ 1 วันก่อนวันปรับพอร์ตจริง</p>` : "";
  el.innerHTML = sectionShell(title, "ทบทวนปีละ 4 ครั้ง (ก.พ. / พ.ค. / ส.ค. / พ.ย.) · กองทุนที่อิงดัชนี MSCI ซื้อขายตามวันปรับพอร์ตจริง", body + nextTxt,
    { link: "https://www.msci.com/quarterly-index-review", source: "MSCI (Public List)" });
}

async function loadMSCI() {
  try {
    const r = await fetch("data/msci.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    renderThMSCI(await r.json());
  } catch (e) { renderThMSCI(null); }
}
loadMSCI();

// ---- เงินต่างชาติในตลาดตราสารหนี้ไทย (ไฟล์แยก data/bondflow.json) ----
const flowWord = (v) => (v >= 0 ? "เข้า" : "ออก");
const flowCls = (v) => (v > 0 ? "up" : v < 0 ? "down" : "");
const flowAbs = (v) => fmt(Math.abs(v), 0);

function weekRange(a, b) {
  const da = new Date(a + "T00:00:00"), db = new Date(b + "T00:00:00");
  const m = (d) => d.toLocaleDateString("th-TH", { month: "short" });
  return da.getMonth() === db.getMonth() ? `${da.getDate()}–${db.getDate()} ${m(db)}` : `${da.getDate()} ${m(da)}–${db.getDate()} ${m(db)}`;
}

function flowVerdict(sec) {
  const w = sec.week, v = w.flow, a = Math.abs(v);
  const inflow = v >= 0;
  let size = "อยู่ในระดับปกติ";
  if (sec.week_p95 && a >= sec.week_p95) size = "<b>มากเป็นพิเศษ</b> (มากกว่า 95% ของช่วง 5 วันใน 2 ปีที่ผ่านมา)";
  else if (sec.week_p80 && a >= sec.week_p80) size = "<b>มากกว่าปกติ</b> (มากกว่า 80% ของช่วง 5 วันใน 2 ปีที่ผ่านมา)";
  // ส่วนไหนเป็นตัวหลัก: ระยะสั้น / ระยะยาว / ตราสารครบอายุ
  const parts = [["st", inflow ? w.st : -w.st], ["lt", inflow ? w.lt : -w.lt], ["exp", inflow ? 0 : w.exp]];
  parts.sort((x, y) => y[1] - x[1]);
  const main = parts[0][1] > 0 ? parts[0][0] : null;
  const why = {
    st: inflow ? "ส่วนใหญ่เป็น <b>เงินระยะสั้น</b> (เงินร้อน) มักเข้ามาเก็งกำไรค่าเงิน/ดอกเบี้ย ช่วยให้เงินบาทแข็ง แต่ออกได้เร็ว"
               : "ส่วนใหญ่เป็น <b>เงินระยะสั้น</b> (เงินร้อน) ไหลออก มักกดดันให้เงินบาทอ่อน",
    lt: inflow ? "ส่วนใหญ่เป็น <b>เงินระยะยาว</b> แปลว่านักลงทุนตั้งใจถือพันธบัตรไทยนาน เป็นสัญญาณความเชื่อมั่น"
               : "ส่วนใหญ่เป็น <b>เงินระยะยาว</b> แปลว่านักลงทุนที่ตั้งใจถือนานกำลังลดการลงทุนในไทย ควรจับตา",
    exp: "ส่วนใหญ่มาจาก <b>พันธบัตรที่ต่างชาติถือครบอายุ</b> (ได้เงินคืน ไม่ได้ขาย) และยังไม่ได้ซื้อใหม่ทดแทน",
  }[main] || "";
  return `<div class="flow-verdict ${inflow ? "in" : "out"}">
    <p class="fv-head">5 วันทำการล่าสุด ต่างชาติ<b class="${flowCls(v)}">${inflow ? "นำเงินเข้า" : "ดึงเงินออก"} ${flowAbs(v)} ล้านบาท</b></p>
    <p>ขนาด${size}</p>${why ? `<p>${why}</p>` : ""}</div>`;
}

function renderThBondFlow(sec) {
  const title = "เงินต่างชาติในตลาดตราสารหนี้ไทย";
  const el = document.getElementById("th-bondflow");
  if (!sec || !sec.ok) { el.innerHTML = failHTML(title, sec); return; }
  const L = sec.latest, H = sec.holding_now;
  const row = (label, sub, x) => `<tr><td>${label}<br><span class="small">${sub}</span></td>
    <td class="num ${flowCls(x.flow)}"><b>${flowWord(x.flow)} ${flowAbs(x.flow)}</b></td>
    <td class="num ${flowCls(x.st)}">${sgn(x.st, 0)}</td><td class="num ${flowCls(x.lt)}">${sgn(x.lt, 0)}</td></tr>`;
  const exps = [["วันล่าสุด", L], ["5 วัน", sec.week], ["เดือนนี้", sec.mtd], ["ต้นปี", sec.ytd]].filter(([, x]) => x.exp > 0)
    .map(([n, x]) => `${n} ${fmt(x.exp, 0)}`).join(" · ");
  const table = `<table class="idx-table flow-table"><thead><tr><th>ช่วงเวลา</th><th class="num">สุทธิ<br><span class="small">(ล้านบาท)</span></th><th class="num">ระยะสั้น</th><th class="num">ระยะยาว</th></tr></thead><tbody>
    ${row("วันล่าสุด", esc(thaiDateShort(L.date)), L)}
    ${row("5 วันทำการ", esc(weekRange(sec.week.from, sec.week.to)), sec.week)}
    ${row("เดือนนี้", esc(thaiMonth(sec.mtd.month)), sec.mtd)}
    ${row("ตั้งแต่ต้นปี", "ปี " + (sec.ytd.year + 543), sec.ytd)}</tbody></table>
    <p class="small flow-note">สุทธิ = ระยะสั้น + ระยะยาว − พันธบัตรที่ต่างชาติถือแล้วครบอายุ${exps ? ` (ครบอายุ: ${exps})` : ""}</p>`;
  const yb = sec.holding_ytd_base, ya = sec.holding_year_ago;
  const cmp = (base, label) => base ? `<span class="${flowCls(H.total - base.total)}">${label} ${sgn(H.total - base.total, 0)}</span>` : "";
  const ltShare = H.total ? Math.round((H.lt / H.total) * 100) : null;
  const hold = `<h3 class="flow-h3">ต่างชาติถือตราสารหนี้ไทยอยู่เท่าไหร่</h3>
    <p class="big-num">${fmt(H.total, 0)} <span class="small">ล้านบาท (≈ ${fmt(H.total / 1e6, 2)} ล้านล้านบาท)</span></p>
    <p class="panel-sub">${cmp(yb, "เทียบต้นปี")} · ${cmp(ya, "เทียบ 1 ปีก่อน")}${ltShare != null ? ` · เป็นระยะยาว ${ltShare}% ระยะสั้น ${100 - ltShare}%` : ""}</p>
    <div id="ch-bond-hold"></div>`;
  const guide = `<details class="details flow-guide"><summary>📖 วิธีอ่านแบบง่ายๆ (แตะเพื่ออ่าน)</summary><ul>
    <li><b>เงินไหลเข้า</b> = ต่างชาติแลกดอลลาร์เป็นเงินบาทมาซื้อพันธบัตรไทย → เงินบาทมักแข็งขึ้น<br><b>เงินไหลออก</b> = ต่างชาติขายพันธบัตรแล้วแลกกลับเป็นดอลลาร์ → เงินบาทมักอ่อนลง</li>
    <li><b>ระยะสั้น</b> (พันธบัตรอายุเหลือไม่เกิน 1 ปี) = เงินร้อน เข้าเร็วออกเร็ว มักมาเก็งกำไรค่าเงิน</li>
    <li><b>ระยะยาว</b> (อายุเหลือเกิน 1 ปี) = นักลงทุนที่ตั้งใจถือนาน สะท้อนความเชื่อมั่นต่อไทยจริงๆ <b>ให้น้ำหนักกับตัวนี้มากกว่า</b></li>
    <li><b>ครบอายุ</b> = พันธบัตรที่ต่างชาติถือหมดอายุ ได้เงินคืน นับเป็นเงินไหลออกด้วย (ถึงจะไม่ได้ขาย)</li>
    <li>ดูคู่กับกล่อง <b>กลุ่มนักลงทุน (ตลาดหุ้น)</b> ด้านบน: ถ้าต่างชาติขายทั้งหุ้นและพันธบัตรพร้อมกัน = เงินต่างชาติกำลังถอนออกจากไทยจริงจัง</li>
    <li>ดูคู่กับกล่อง <b>yield พันธบัตรไทย</b> ด้านล่าง: ต่างชาติขายหนักมักทำให้ yield ขึ้น</li></ul></details>`;
  const partial = L.partial ? `<p class="stale">⏳ ข้อมูลวันนี้ยังไม่ครบ: ${esc(L.partial)}</p>` : "";
  const info = `<p class="update-info">📅 ข้อมูล ณ <b>${esc(thaiDate(L.date))}</b> · ปรับปรุง: ${esc(sec.freq)}<br>
    ยอดถือครองคิดตามมูลค่าที่ตราไว้ และอาจถูกปรับเล็กน้อยช่วงสัปดาห์ที่ 3 ของเดือน</p>`;
  el.innerHTML = sectionShell(title, "เงินต่างชาติไหลเข้า/ออกพันธบัตรและหุ้นกู้ไทย · ตัวช่วยดู fund flow และทิศทางเงินบาท",
    flowVerdict(sec) + partial + table + guide +
    `<h3 class="flow-h3">เงินเข้า/ออกรายเดือน ย้อนหลัง 24 เดือน</h3>
     <p class="small">แท่งเขียว = เงินไหลเข้า · แท่งแดง = เงินไหลออก · หน่วยพันล้านบาท · เดือนล่าสุดยังไม่ครบเดือน</p>
     <div id="ch-bond-month"></div>` + hold + info, sec);
  chartBox("ch-bond-month", { height: 190, series: [{ data: sec.monthly.map((m) => [m.month + "-15", m.flow]), type: "bar", color: C.green, label: "" }],
    yFmt: (v) => fmt(v / 1000, 0), tipFmt: (v) => (v >= 0 ? "ไหลเข้า " : "ไหลออก ") + flowAbs(v) + " ล้านบาท",
    tipDate: (d) => thaiMonth(d.slice(0, 7)) });
  chartBox("ch-bond-hold", { series: [{ data: sec.holding.total, color: C.blue, label: "ยอดถือครอง" }],
    yFmt: (v) => fmt(v, 0), tipFmt: (v) => fmt(v, 1) + " พันล้านบาท" });
}

async function loadBondFlow() {
  try {
    const r = await fetch("data/bondflow.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("โหลดไฟล์ข้อมูลไม่ได้ (HTTP " + r.status + ")");
    renderThBondFlow(await r.json());
  } catch (e) {
    console.error(e);
    try { renderThBondFlow({ ok: false, error: e.message }); } catch (_) {}
  }
}
loadBondFlow();

// ---- ข้อมูลเสริมจาก settfex (ไฟล์แยก data/settfex.json) ----
function renderThYields(sec) {
  const title = "อัตราผลตอบแทนพันธบัตรรัฐบาลไทย";
  extraPanel("th-yields", title, sec, () => {
    const L = sec.latest;
    const rows = (sec.curve || []).map((r) => {
      const ch = r.year_ago == null ? null : r.now - r.year_ago;
      return `<tr><td>${esc(r.tenor.replace("M", " เดือน").replace("Y", " ปี"))}</td><td class="num">${fmt(r.now, 2)}%</td>
        <td class="num">${r.year_ago == null ? "–" : fmt(r.year_ago, 2) + "%"}</td>
        <td class="num ${ch > 0 ? "up" : ch < 0 ? "down" : ""}">${ch == null ? "–" : sgn(ch)}</td></tr>`;
    }).join("");
    return `<p class="big-num">10 ปี ${pct(L.y10)} · 2 ปี ${pct(L.y2)}</p>
      <p class="panel-sub">ส่วนต่าง 10 ปี − 2 ปี = <b class="${L.spread < 0 ? "neg" : ""}">${sgn(L.spread)}%</b> · yield ระยะสั้นสะท้อนความคาดหวังดอกเบี้ยนโยบาย กนง. ส่วนระยะยาวสะท้อนมุมมองเศรษฐกิจและเงินเฟ้อ</p>
      ${legendHTML([[C.blue, "10 ปี"], [C.purple, "2 ปี"]])}<div id="ch-th-yields"></div>
      ${legendHTML([[C.gold, "ส่วนต่าง 10 ปี − 2 ปี"]])}<div id="ch-th-spread"></div>
      <table class="idx-table"><thead><tr><th>อายุ</th><th class="num">ล่าสุด</th><th class="num">1 ปีก่อน<br><span class="small">${esc(thaiDateShort(sec.year_ago_date))}</span></th><th class="num">เปลี่ยน</th></tr></thead><tbody>${rows}</tbody></table>
      ${infoHTML(sec, L.date)}`;
  });
  if (sec && sec.ok) {
    chartBox("ch-th-yields", { series: [{ data: sec.y10, color: C.blue, label: "10 ปี" }, { data: sec.y2, color: C.purple, label: "2 ปี" }], yFmt: (v) => fmt(v, 1) + "%", tipFmt: (v) => fmt(v, 2) + "%" });
    chartBox("ch-th-spread", { height: 130, zero: true, series: [{ data: sec.spread, color: C.gold, label: "ส่วนต่าง", width: 1.6 }], yFmt: (v) => fmt(v, 1), tipFmt: (v) => sgn(v) + "%" });
  }
}

async function loadSettfex() {
  let d = null;
  try {
    const r = await fetch("data/settfex.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("โหลดไฟล์ข้อมูลไม่ได้ (HTTP " + r.status + ")");
    d = await r.json();
    renderThYields(d.th_yields);
  } catch (e) {
    console.error(e);
    try { renderThYields({ ok: false, error: e.message }); } catch (_) {}
  }
}
loadSettfex();

async function loadTH() {
  const upd = document.getElementById("th-updated");
  try {
    const r = await fetch("data/th.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const d = await r.json();
    upd.textContent = "อัปเดตล่าสุด: " + thaiDateTime(d.updated_at) + " (เวลาไทย)";
    for (const [fn, sec] of [[renderThGDP, d.gdp], [renderThMPC, d.mpc], [renderThCPI, d.cpi], [renderThExport, d.exports], [renderThInvestor, d.investor]]) {
      try { fn(sec); } catch (e) { console.error(e); }
    }
  } catch (e) {
    upd.innerHTML = `<span class="fail">ดึงข้อมูลไม่สำเร็จ</span> โหลดไฟล์ข้อมูลไทยไม่ได้ (${esc(e.message)})`;
  }
}

loadTH();

// ============================================================
// หน้า 1: ภาพวงกลมขนาดตลาด/ดัชนีสหรัฐฯ + VIX
// ============================================================
// พื้นที่ของวงกลมรัศมี r ที่อยู่ "ซ้าย" ของเส้นแนวตั้งซึ่งห่างจากจุดศูนย์กลางไปทางขวา h
function leftArea(h, r) {
  h = Math.max(-r, Math.min(r, h));
  const seg = (d) => r * r * Math.acos(d / r) - d * Math.sqrt(r * r - d * d);
  return h >= 0 ? Math.PI * r * r - seg(h) : seg(-h);
}
// หา h ที่ทำให้สัดส่วนพื้นที่ด้านซ้าย = frac
function solveH(frac, r) {
  let lo = -r, hi = r;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    if (leftArea(mid, r) / (Math.PI * r * r) < frac) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

function drawUniverse(box, u) {
  const W = Math.max(280, box.clientWidth || 320);
  const R = Math.min(W * 0.46, 210), H = 2 * R + 16;
  const cx = W / 2, cy = R + 8;
  const total = u.nyse.cap + u.nasdaq.cap;
  const k = (Math.PI * R * R) / total; // พื้นที่ต่อ 1 ดอลลาร์
  const chordX = cx + solveH(u.nyse.cap / total, R);
  const rs = Math.sqrt((u.sp500.cap * k) / Math.PI);
  let sx = chordX - solveH(u.sp500.nyse_frac, rs);
  sx = Math.max(cx - (R - rs), Math.min(cx + (R - rs), sx)); // ต้องอยู่ในวงใหญ่
  const rd = Math.sqrt((u.dow.cap * k) / Math.PI);
  let dx = chordX - solveH(u.dow.nyse_frac, rd);
  dx = Math.max(sx - (rs - rd), Math.min(sx + (rs - rd), dx)); // ต้องอยู่ในวง S&P 500
  const dy = cy - Math.min(rs - rd - Math.abs(dx - sx), rs * 0.25) * 0.6; // ยก Dow ขึ้นเล็กน้อยให้ดูง่าย

  box.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="universe-svg">
    <defs><clipPath id="u-big"><circle cx="${cx}" cy="${cy}" r="${R}"/></clipPath></defs>
    <g clip-path="url(#u-big)">
      <rect x="${cx - R}" y="${cy - R}" width="${chordX - (cx - R)}" height="${2 * R}" fill="#378ADD" opacity=".38"/>
      <rect x="${chordX}" y="${cy - R}" width="${cx + R - chordX}" height="${2 * R}" fill="#7F77DD" opacity=".38"/>
    </g>
    <circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="#8b98a8" stroke-width="1"/>
    <line x1="${chordX}" x2="${chordX}" y1="${cy - Math.sqrt(R * R - (chordX - cx) ** 2)}" y2="${cy + Math.sqrt(R * R - (chordX - cx) ** 2)}" stroke="#e6edf3" stroke-width="1.2" stroke-dasharray="5 4" opacity=".7"/>
    <circle cx="${sx}" cy="${cy}" r="${rs}" fill="#EF9F27" fill-opacity=".30" stroke="#EF9F27" stroke-width="2.2"/>
    <circle cx="${dx}" cy="${dy}" r="${rd}" fill="#E24B4A" fill-opacity=".45" stroke="#ff7b7a" stroke-width="2.2"/>
    <text x="${cx - R * 0.72}" y="${cy - R * 0.62}" class="u-label">NYSE</text>
    <text x="${cx + R * 0.72}" y="${cy - R * 0.62}" class="u-label" text-anchor="end">Nasdaq</text>
    <text x="${dx}" y="${dy + 5}" class="u-label" text-anchor="middle">Dow</text>
    <text x="${sx}" y="${cy + rs * 0.72}" class="u-label" text-anchor="middle">S&amp;P 500</text>
  </svg>`;
}

function renderUniverse(u) {
  const el = document.getElementById("w-universe");
  const title = "ขนาดตลาดหุ้นสหรัฐฯ และดัชนี (พื้นที่ = Market Cap)";
  if (!u || !u.nyse) { el.innerHTML = failHTML(title, u); return; }
  const total = u.nyse.cap + u.nasdaq.cap;
  const T = (v) => "$" + fmt(v / 1e12, 1) + "T";
  const share = (v) => fmt((v / total) * 100, 0) + "%";
  const item = (color, name, cap, extra) =>
    `<li><i style="background:${color}"></i><b>${name}</b> ${T(cap)} <span class="small">${extra}</span></li>`;
  el.innerHTML = `<h2>${title}</h2>
    <p class="panel-sub">วงใหญ่ = ตลาดหุ้นสหรัฐฯ ทั้งหมด แบ่งเป็นฝั่ง NYSE | Nasdaq (เส้นประ) · S&amp;P 500 คร่อมทั้ง 2 ตลาด · Dow อยู่ใน S&amp;P 500</p>
    <div id="universe-box"></div>
    <ul class="u-legend">
      ${item("#378ADD", "NYSE Composite", u.nyse.cap, `${fmt(u.nyse.count, 0)} ตัว`)}
      ${item("#7F77DD", "Nasdaq Composite", u.nasdaq.cap, `${fmt(u.nasdaq.count, 0)} ตัว`)}
      ${item("#EF9F27", "S&amp;P 500", u.sp500.cap, `= ${share(u.sp500.cap)} ของทั้งตลาด · อยู่ NYSE ${fmt(u.sp500.nyse_frac * 100, 0)}% / Nasdaq ${fmt(100 - u.sp500.nyse_frac * 100, 0)}%`)}
      ${item("#E24B4A", "Dow Jones (30 ตัว)", u.dow.cap, `= ${share(u.dow.cap)} ของทั้งตลาด · อยู่ NYSE ${fmt(u.dow.nyse_frac * 100, 0)}% / Nasdaq ${fmt(100 - u.dow.nyse_frac * 100, 0)}%`)}
    </ul>
    <p class="small">ขนาดพื้นที่ใกล้เคียงสัดส่วนจริง (วงกลมซ้อนกันหลายชั้นให้ตรงทุกส่วนทางเรขาคณิตไม่ได้)</p>
    <p class="update-info">📅 ภาพนี้เป็นข้อมูลวันที่ <b>${esc(thaiDate(u.asof))}</b> · ปรับปรุง: ${esc(u.freq)}<br>
      ⏭ สร้างภาพใหม่ครั้งถัดไปประมาณ <b>${esc(thaiDate(u.next))}</b></p>
    <div class="panel-foot"><span class="src">ที่มา: ${esc(u.source)} · Nasdaq Trader</span></div>`;
  const box = document.getElementById("universe-box");
  const render = () => drawUniverse(box, u);
  CHARTS["universe-box"] = render;
  render();
}

function renderVIX(v) {
  const el = document.getElementById("w-vix");
  const title = "VIX (ดัชนีความกลัว)";
  if (!v || !v.ok) { el.innerHTML = failHTML(title, v); return; }
  const L = v.latest;
  const zone = L.value >= 30 ? ["กลัวมาก", "var(--down)"] : L.value >= 18 ? ["ปกติ / เริ่มกังวล", "var(--warn)"] : ["ตลาดชิล / โลภ", "var(--up)"];
  el.innerHTML = sectionShell(title, "", `
    <p class="big-num">${fmt(L.value, 2)} <span class="small" style="color:${zone[1]}">● ${zone[0]}</span></p>
    <p class="panel-sub">ความผันผวนที่ตลาดคาดใน S&amp;P 500 อีก 30 วัน · ต่ำกว่า 18 = ตลาดชิล/โลภ · 18–30 = ปกติ/เริ่มกังวล · เกิน 30 = กลัวมาก · ย้อนหลัง 2 ปี</p>
    <div id="ch-vix"></div>
    <p class="update-info">📅 ข้อมูล ณ <b>${esc(thaiDate(L.date))}</b> · ปรับปรุงทุก 3 ชั่วโมง (พร้อมดัชนีด้านบน)</p>`, v);
  chartBox("ch-vix", {
    height: 210, yInclude: [10, 34],
    series: [{ data: v.data, color: "#e6edf3", label: "VIX", width: 1.6 }],
    bands: [
      { from: -100, to: 18, color: "#2fbf71", label: "โลภ" },
      { from: 18, to: 30, color: "#f2b33d", label: "ปกติ" },
      { from: 30, to: 1000, color: "#f0566a", label: "กลัว" },
    ],
    hlines: [{ y: 30, color: "#f0566a", label: "30" }, { y: 18, color: "#2fbf71", label: "18" }],
    yFmt: (x) => fmt(x, 0), tipFmt: (x) => fmt(x, 2),
  });
}

function renderSoxx(v) {
  const el = document.getElementById("w-soxx");
  const title = "SOXX / S&amp;P 500 (หุ้นชิปนำตลาดไหม)";
  if (!v || !v.ok) { el.innerHTML = failHTML(title, v); return; }
  const L = v.latest, up = L.vs_ma200 > 0, rising = L.chg_3m > 0;
  const st = up && rising ? ["up", "หุ้นชิปนำตลาด → เอนไปทาง Risk-on (กล้าเสี่ยง)"]
    : !up && !rising ? ["out", "หุ้นชิปแพ้ตลาด → เอนไปทาง Risk-off (ระวังตัว)"]
    : ["mid", "ยังไม่ชัด / กำลังเปลี่ยนทิศ"];
  el.innerHTML = sectionShell(title, "", `
    <div class="flow-verdict ${st[0] === "up" ? "in" : st[0] === "out" ? "out" : "mid"}">
      <p class="fv-head">ตอนนี้: <b class="${st[0] === "up" ? "up" : st[0] === "out" ? "down" : "warn"}">${st[1]}</b></p>
      <p>${up ? "อยู่เหนือ" : "อยู่ใต้"}เส้นเฉลี่ย 200 วัน ${sgn(L.vs_ma200, 1)}% · 3 เดือนล่าสุด ${sgn(L.chg_3m, 1)}%</p>
    </div>
    ${legendHTML([["#e6edf3", "SOXX ÷ S&P 500 (เริ่ม = 100)"], ["#ffd479", "เฉลี่ย 200 วัน", true]])}
    <div id="ch-soxx"></div>
    <ul class="soxx-guide">
      <li><b class="up">เส้นขึ้น</b> = หุ้นชิปชนะตลาด เงินไหลเข้าหุ้นเติบโต มักเกิดตอนเศรษฐกิจดี/ดอกเบี้ยขาลง → <b>Risk-on</b></li>
      <li><b class="down">เส้นลง</b> = หุ้นชิปแพ้ตลาด เงินย้ายไปหุ้นปลอดภัย มักเกิดตอนเงินเฟ้อ/ดอกเบี้ยขึ้น/กลัวถดถอย → <b>Risk-off</b></li>
      <li>ดูคู่กับ VIX ด้านบน: เส้นนี้ขึ้น + VIX ต่ำ = Risk-on ชัดเจน</li>
    </ul>
    <p class="update-info">📅 ข้อมูล ณ <b>${esc(thaiDate(L.date))}</b> · ปรับปรุงทุก 3 ชั่วโมง (พร้อมดัชนีด้านบน)</p>`, v);
  chartBox("ch-soxx", {
    height: 210,
    series: [{ data: v.data, color: "#e6edf3", label: "SOXX/S&P", width: 1.6 },
             { data: v.ma200, color: "#ffd479", label: "เฉลี่ย 200 วัน", width: 1.4, dash: true, noDot: true }],
    hlines: [{ y: 100, color: "#8b98a8", label: "100" }],
    yFmt: (x) => fmt(x, 0), tipFmt: (x) => fmt(x, 1),
  });
}

async function loadUniverse() {
  try {
    const r = await fetch("data/universe.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    renderUniverse(await r.json());
  } catch (e) {
    renderUniverse({ error: "โหลดข้อมูลไม่ได้ (" + e.message + ")" });
  }
}
loadUniverse();
