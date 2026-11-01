// Bonnes Affaires — affichage des offres collectées par le robot (data/deals.json)
(() => {
  const PAGE = 24;
  const state = { offres: [], categories: [], cat: "Toutes", q: "", sort: "recent", shown: PAGE };

  const $ = (id) => document.getElementById(id);
  const grid = $("grid"), status = $("status"), more = $("more"), tpl = $("card");

  const euro = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
  const rtf = new Intl.RelativeTimeFormat("fr", { numeric: "auto" });
  const norm = (s) => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

  function ago(iso) {
    const min = Math.round((Date.now() - Date.parse(iso)) / 60000);
    if (min < 60) return rtf.format(-Math.max(min, 1), "minute");
    if (min < 1440) return rtf.format(-Math.round(min / 60), "hour");
    return rtf.format(-Math.round(min / 1440), "day");
  }

  function safeUrl(u) {
    try { const url = new URL(u); return url.protocol === "https:" || url.protocol === "http:" ? url.href : null; }
    catch { return null; }
  }

  // Lit l'état depuis l'adresse (#cat=High-tech&q=ssd) pour pouvoir partager un lien filtré.
  function readHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    state.cat = p.get("cat") || "Toutes";
    state.q = p.get("q") || "";
    state.sort = p.get("tri") || "recent";
    $("q").value = state.q;
    $("sort").value = state.sort;
  }
  function writeHash() {
    const p = new URLSearchParams();
    if (state.cat !== "Toutes") p.set("cat", state.cat);
    if (state.q) p.set("q", state.q);
    if (state.sort !== "recent") p.set("tri", state.sort);
    history.replaceState(null, "", p.toString() ? "#" + p : location.pathname);
  }

  function filtered() {
    const words = norm(state.q).split(/\s+/).filter(Boolean);
    let list = state.offres.filter((o) =>
      (state.cat === "Toutes" || o.categorie === state.cat) &&
      words.every((w) => norm(`${o.titre} ${o.marchand} ${o.source}`).includes(w)));
    const byPrice = (a, b, dir) => (a.prix ?? Infinity * dir) - (b.prix ?? Infinity * dir);
    if (state.sort === "prix-asc") list.sort((a, b) => byPrice(a, b, 1));
    else if (state.sort === "prix-desc") list.sort((a, b) => byPrice(b, a, -1));
    else if (state.sort === "populaire") list.sort((a, b) => (b.populaire - a.populaire) || b.date.localeCompare(a.date));
    else list.sort((a, b) => b.date.localeCompare(a.date));
    return list;
  }

  function renderChips() {
    const box = $("cats");
    box.textContent = "";
    for (const c of ["Toutes", ...state.categories]) {
      const n = c === "Toutes" ? state.offres.length : state.offres.filter((o) => o.categorie === c).length;
      const b = document.createElement("button");
      b.className = "chip";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", String(c === state.cat));
      b.textContent = c;
      const s = document.createElement("span");
      s.className = "n";
      s.textContent = n;
      b.append(s);
      b.onclick = () => { state.cat = c; state.shown = PAGE; update(); };
      box.append(b);
    }
  }

  function card(o) {
    const href = safeUrl(o.lien);
    if (!href) return null;
    const node = tpl.content.cloneNode(true);
    const a = node.querySelector(".card-link");
    a.href = href;
    a.title = `Voir l'offre sur ${o.source}`;
    const thumb = node.querySelector(".thumb");
    const img = o.image && safeUrl(o.image);
    if (img) {
      const el = document.createElement("img");
      el.src = img; el.alt = ""; el.loading = "lazy"; el.referrerPolicy = "no-referrer";
      el.onerror = () => { el.remove(); thumb.append(placeholder(o)); };
      thumb.append(el);
    } else thumb.append(placeholder(o));
    node.querySelector(".cat").textContent = o.categorie;
    node.querySelector(".hot").hidden = !o.populaire;
    node.querySelector(".title").textContent = o.titre;
    node.querySelector(".price").textContent = o.prix == null ? "Voir le prix" : o.prix === 0 ? "Gratuit" : euro.format(o.prix);
    node.querySelector(".merchant").textContent = o.marchand ? `chez ${o.marchand}` : "";
    node.querySelector(".when").textContent = `${o.source} · ${ago(o.date)}`;
    return node;
  }
  function placeholder(o) {
    const s = document.createElement("span");
    s.className = "ph";
    s.textContent = o.marchand || o.categorie;
    return s;
  }

  function update() {
    writeHash();
    renderChips();
    const list = filtered();
    grid.textContent = "";
    for (const o of list.slice(0, state.shown)) { const c = card(o); if (c) grid.append(c); }
    status.textContent = list.length
      ? `${list.length} offre${list.length > 1 ? "s" : ""}${state.cat !== "Toutes" ? " en " + state.cat : ""}${state.q ? ` pour « ${state.q} »` : ""}`
      : "Aucune offre ne correspond à votre recherche.";
    more.hidden = list.length <= state.shown;
  }

  let t;
  $("q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { state.q = e.target.value.trim(); state.shown = PAGE; update(); }, 150); });
  $("sort").addEventListener("change", (e) => { state.sort = e.target.value; update(); });
  more.addEventListener("click", () => { state.shown += PAGE; update(); });

  fetch("data/deals.json", { cache: "no-cache" })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => {
      state.offres = data.offres || [];
      state.categories = data.categories || [];
      if (data.mis_a_jour) {
        $("updated").textContent = "Dernière mise à jour : " + new Date(data.mis_a_jour).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
      }
      readHash();
      if (!state.offres.length) { status.textContent = "Les premières offres arrivent bientôt : le robot de collecte n'a pas encore tourné."; renderChips(); return; }
      update();
    })
    .catch(() => { status.textContent = "Impossible de charger les offres pour le moment. Réessayez dans quelques minutes."; });
})();
