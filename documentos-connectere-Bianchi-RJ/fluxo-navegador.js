// Colar no navegador já logado no +Gestão, com a fazenda certa no cabeçalho
// e o receptor.py escutando em 127.0.0.1:8765 na pasta dessa fazenda.
// Preencha CONFIG e rode listar(). Depois baixar(150) até o índice chegar no total.
// Não baixa XML. Não usa o PDF de impressão notas_fiscais/{id}.pdf?l=1.

const CONFIG = {
  produtor: "Claudio Bianchi",
  fazenda: "PJ - Faz Bianchi",
  dataInicio: "01/11/2026",
  dataFim: "30/11/2026",
  // Vazio = produtor inteiro. 304343 = Fabiane na base do Claudio.
  // 304372 = Elenise na base do Carlos (aí produtor/fazenda são Carlos / PJ - Carlos).
  enderecoRemetenteId: "",
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function slug(s) {
  return (s || "s").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 36) || "s";
}

function extensao(nome, mime) {
  const n = (nome || "").toLowerCase();
  const m = (mime || "").toLowerCase();
  if (m.includes("xml") || n.endsWith(".xml")) return null;
  if (m.includes("pdf") || n.endsWith(".pdf")) return "pdf";
  if (m.includes("png") || n.endsWith(".png")) return "png";
  if (m.includes("gif") || n.endsWith(".gif")) return "gif";
  if (m.includes("webp") || n.endsWith(".webp")) return "webp";
  if (m.includes("jpeg") || m.includes("jpg") || /\.jpe?g$/.test(n)) return "jpg";
  return null;
}

function urlAbsoluta(u) {
  const x = u.startsWith("http") ? u : "https://maisgestao.connectere.agr.br" + u;
  return x.replace("/rails/active_storage/blobs/redirect/", "/rails/active_storage/blobs/proxy/");
}

function linhaCsv(row, situacao) {
  return [row.id, row.data, row.numero, (row.fornecedor || "").replace(/;/g, ","), row.operacao, row.total || "", situacao].join(";") + "\n";
}

async function listar() {
  const q = new URLSearchParams({
    "q[com_valor]": "0",
    "q[data_gteq]": CONFIG.dataInicio,
    "q[data_lteq]": CONFIG.dataFim,
    "q[operacao_compras]": "1",
    "q[operacao_vendas]": "0",
    "q[pedido_id_eq]": "",
  });
  if (CONFIG.enderecoRemetenteId) q.set("q[endereco_remetente_id_eq]", String(CONFIG.enderecoRemetenteId));
  const base = "https://maisgestao.connectere.agr.br/notas_fiscais?" + q.toString();
  const rows = [];
  let maxPage = 1;
  for (let page = 1; page <= 80; page++) {
    const url = page === 1 ? base : base + "&page=" + page;
    const html = await (await fetch(url, { credentials: "include" })).text();
    if (html.includes("Acesse a sua conta")) return { login: false };
    const doc = new DOMParser().parseFromString(html, "text/html");
    if (page === 1) {
      window.__ctx = {
        prod: doc.querySelector("#produtor")?.textContent?.trim(),
        emp: doc.querySelector("#empresa")?.textContent?.trim(),
      };
      if (window.__ctx.prod !== CONFIG.produtor || window.__ctx.emp !== CONFIG.fazenda) {
        return { contextoErrado: window.__ctx, esperado: CONFIG };
      }
      const pages = [...doc.querySelectorAll(".pagination a")].map((a) => parseInt(a.textContent, 10)).filter((n) => !isNaN(n));
      if (pages.length) maxPage = Math.max(...pages);
    }
    const found = [...doc.querySelectorAll("tbody tr[id^=nota_fiscal_]")];
    if (!found.length) break;
    for (const tr of found) {
      const tds = [...tr.querySelectorAll(":scope > td")].map((td) => td.innerText.replace(/\s+/g, " ").trim());
      rows.push({
        id: tr.id.replace("nota_fiscal_", ""),
        data: tds[1] || "",
        numero: tds[2] || "",
        fornecedor: tds[3] || "",
        operacao: tds[4] || "",
        total: tds[5] || "",
      });
    }
    if (page >= maxPage) break;
  }
  const map = new Map();
  for (const r of rows) map.set(r.id, r);
  window.__rows = [...map.values()];
  window.__b = 0;
  window.__bstats = { salvos: 0, sem: 0, erros: 0 };
  window.__sem = [];
  const lista = "id;data;numero;fornecedor;operacao;valor\n" + window.__rows.map((r) => linhaCsv(r, "").replace(/;\n$/, "\n")).join("");
  await fetch("http://127.0.0.1:8765/", { method: "POST", headers: { "Content-Type": "text/plain", "X-Filename": "_lista.csv" }, body: lista });
  await fetch("http://127.0.0.1:8765/", { method: "POST", headers: { "Content-Type": "text/plain", "X-Filename": "_andamento.csv" }, body: "id;tipo;arquivo;bytes\n" });
  await fetch("http://127.0.0.1:8765/", { method: "POST", headers: { "Content-Type": "text/plain", "X-Filename": "_sem_arquivo.csv" }, body: "id;data;numero;fornecedor;operacao;valor;situacao\n" });
  return { ctx: window.__ctx, n: window.__rows.length, bruto: rows.length, maxPage, first: window.__rows[0], last: window.__rows.at(-1) };
}

async function arquivos(row) {
  let html = null;
  let last = "";
  for (let t = 0; t < 4; t++) {
    try {
      html = await (await fetch("https://maisgestao.connectere.agr.br/notas_fiscais/" + row.id, { credentials: "include" })).text();
      if (html.includes("Acesse a sua conta")) throw new Error("sessao");
      if (html.includes("Registro não encontrado")) return { ausente: true };
      if (!html.includes("arquivos_modal")) throw new Error("sem_modal");
      if (!html.includes(CONFIG.produtor) || !html.includes(CONFIG.fazenda)) throw new Error("contexto");
      break;
    } catch (e) {
      last = String(e);
      html = null;
      await sleep(350 * (t + 1));
    }
  }
  if (!html) return { erro: last.slice(0, 80) };
  const doc = new DOMParser().parseFromString(html, "text/html");
  const files = [];
  const danfe = doc.querySelector('a[href*="danfe.pdf"]');
  if (danfe) files.push({ url: danfe.getAttribute("href"), tipo: "danfe", ext: "pdf" });
  const modal = doc.querySelector("#arquivos_modal");
  if (modal) {
    let n = 0;
    for (const tr of modal.querySelectorAll("tr[data-url]")) {
      const tds = [...tr.querySelectorAll("td")].map((td) => td.textContent.trim());
      const ext = extensao(tds[0], tds[1]);
      if (!ext) continue;
      n++;
      files.push({ url: tr.getAttribute("data-url"), tipo: n === 1 ? "anexo" : "anexo" + n, ext });
    }
  }
  return { files };
}

async function salvar(row, file) {
  const abs = urlAbsoluta(file.url);
  let buf = null;
  for (let t = 0; t < 3; t++) {
    try {
      const r = await fetch(abs, { credentials: "include" });
      if (!r.ok) return { erro: r.status };
      const ct = r.headers.get("content-type") || "";
      if (/xml|html/i.test(ct)) return { ignorado: ct };
      buf = await r.arrayBuffer();
      break;
    } catch (e) {
      if (t === 2) return { erro: String(e).slice(0, 80) };
      await sleep(400);
    }
  }
  if (!buf || buf.byteLength < 80) return { erro: "pequeno" };
  const data = (row.data || "0000-00-00").split("/").reverse().join("-");
  const num = (row.numero || "sn").replace(/[^a-zA-Z0-9]+/g, "") || "sn";
  const fname = `${data}_${num}_${slug(row.fornecedor)}_${row.id}_${file.tipo}.${file.ext}`;
  const resp = await fetch("http://127.0.0.1:8765/", {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream", "X-Filename": fname },
    body: buf,
  });
  if (!resp.ok) return { erro: "save" };
  await fetch("http://127.0.0.1:8765/", {
    method: "POST",
    headers: { "Content-Type": "text/plain", "X-Filename": "_andamento.csv" },
    body: `${row.id};${file.tipo};${fname};${buf.byteLength}\n`,
  });
  return { ok: true, bytes: buf.byteLength };
}

async function baixar(qtd) {
  const fim = Math.min(window.__rows.length, window.__b + qtd);
  let cursor = window.__b;
  let salvos = 0;
  let sem = 0;
  let erros = 0;
  let bytes = 0;
  const det = [];
  async function worker() {
    while (true) {
      const i = cursor++;
      if (i >= fim) return;
      const row = window.__rows[i];
      try {
        const got = await arquivos(row);
        if (got.ausente) {
          window.__sem.push(row);
          await fetch("http://127.0.0.1:8765/", {
            method: "POST",
            headers: { "Content-Type": "text/plain", "X-Filename": "_sem_arquivo.csv" },
            body: linhaCsv(row, "registro_nao_encontrado"),
          });
          sem++;
          continue;
        }
        if (got.erro) {
          erros++;
          if (det.length < 6) det.push({ id: row.id, err: got.erro });
          continue;
        }
        if (!got.files.length) {
          sem++;
          window.__sem.push(row);
          await fetch("http://127.0.0.1:8765/", {
            method: "POST",
            headers: { "Content-Type": "text/plain", "X-Filename": "_sem_arquivo.csv" },
            body: linhaCsv(row, "sem_arquivo"),
          });
          continue;
        }
        let algum = false;
        for (const f of got.files) {
          const res = await salvar(row, f);
          if (res && res.ok) {
            salvos++;
            bytes += res.bytes;
            algum = true;
          } else if (res && res.ignorado) {
            continue;
          } else {
            erros++;
            if (det.length < 6) det.push({ id: row.id, res });
          }
        }
        if (!algum) {
          window.__sem.push(row);
          await fetch("http://127.0.0.1:8765/", {
            method: "POST",
            headers: { "Content-Type": "text/plain", "X-Filename": "_sem_arquivo.csv" },
            body: linhaCsv(row, "arquivo_indisponivel"),
          });
        }
      } catch (e) {
        erros++;
        if (det.length < 6) det.push({ id: row.id, err: String(e).slice(0, 80) });
      }
    }
  }
  await Promise.all([worker(), worker()]);
  window.__b = fim;
  window.__bstats.salvos += salvos;
  window.__bstats.sem += sem;
  window.__bstats.erros += erros;
  return { i: window.__b, total: window.__rows.length, salvos, sem, erros, mb: Math.round((bytes / 1024 / 1024) * 10) / 10, det, acum: window.__bstats, ctx: window.__ctx };
}

window.listar = listar;
window.baixar = baixar;
