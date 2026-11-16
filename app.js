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
const SHORT = { spx: "S&P 500", nasdaq: "NASDAQ", set: "SET", hscei: "HSCEI", sse: "SSE (000001)", vni: "VN-Index" };
const CUR = { USD: "$", THB: "฿", HKD: "HK$", CNY: "¥", VND: "₫" };

function fmtCap(v, cur) {
  const sym = CUR[cur] || "";
  if (v >= 1e12) return `${sym}${fmt(v / 1e12, 2)}T`;
  if (v >= 1e9) return `${sym}${fmt(v / 1e9, 2)}B`;
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
  const date = L.value != null ? esc(thaiDate(L.asof)) : "–";
  return `<tr>
    <td class="name">${esc(SHORT[x.id] || x.name)}</td>
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
    grid.innerHTML = `
      <table class="idx-table">
        <thead><tr>
          <th>ดัชนี</th><th class="num">ระดับ (จุด)</th><th class="num">Market Cap</th>
          <th class="num">P/E</th><th class="num">P/BV</th><th>ข้อมูล ณ</th>
        </tr></thead>
        <tbody>${data.indices.map(rowHTML).join("")}</tbody>
      </table>
      <p class="legend"><span class="fail">ดึงไม่สำเร็จ</span> = ดึงข้อมูลไม่สำเร็จ · – = ยังไม่มีแหล่งข้อมูล · ⚠ = ข้อมูลเก่า · T = ล้านล้าน, B = พันล้าน</p>
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

function renderGDP(sec) {
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
    `<table class="idx-table"><thead><tr><th>ไตรมาส</th><th class="num">GDP Growth (QoQ)</th><th class="num">ขนาด GDP</th></tr></thead><tbody>${rows}</tbody></table>`,
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

function renderCPI(sec) {
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
    `<table class="idx-table"><thead><tr><th>เดือน</th><th class="num">CPI YoY</th></tr></thead><tbody>${rows}</tbody></table>${notes}`,
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
    for (const [fn, sec] of [[renderGDP, d.gdp], [renderFed, d.fed], [renderCPI, d.cpi]]) {
      try { fn(sec); } catch (e) { console.error(e); }
    }
  } catch (e) {
    upd.innerHTML = `<span class="fail">ดึงข้อมูลไม่สำเร็จ</span> โหลดไฟล์ข้อมูลอเมริกาไม่ได้ (${esc(e.message)})`;
  }
}

loadUS();
