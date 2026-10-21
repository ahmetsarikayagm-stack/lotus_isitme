/*
 * Formlarda:
 *  1) select[data-cascade-parent="id_x"]  -> üst alana göre seçenekleri süzer (Kategori > Marka > Model)
 *  2) select[data-filterable="placeholder"] -> select'in üstüne arama kutusu ekler
 * Sonradan eklenen satırlar için: LotusCascade.init(satirElementi)
 */
(function () {
  const registry = [];

  function rebuild(w, keep) {
    const pv = w.parent.value;
    w.child.innerHTML = "";
    w.all.forEach((o) => {
      if (o.value === "" || (pv !== "" && o.parent === pv)) w.child.add(new Option(o.text, o.value));
    });
    w.child.value = keep;
    if (w.child.value !== keep) w.child.value = "";
    w.child.disabled = pv === "";
  }

  function cascade(parentEl) {
    registry.filter((w) => w.parent === parentEl).forEach((w) => {
      rebuild(w, "");
      cascade(w.child);
    });
  }

  function initCascade(root) {
    const fresh = Array.from(root.querySelectorAll("select[data-cascade-parent]:not([data-cascade-bound])"))
      .map((child) => ({
        child,
        parent: document.getElementById(child.dataset.cascadeParent),
        all: Array.from(child.options).map((o) => ({ value: o.value, text: o.textContent, parent: o.dataset.parent || "" })),
        initial: child.value,
      }))
      .filter((w) => w.parent);

    fresh.forEach((w) => { w.child.dataset.cascadeBound = "1"; registry.push(w); });
    fresh.forEach((w) => {
      if (!w.parent.dataset.cascadeListener) {
        w.parent.dataset.cascadeListener = "1";
        w.parent.addEventListener("change", () => cascade(w.parent));
      }
    });
    fresh.forEach((w) => rebuild(w, w.initial)); // DOM sırası: üst alan önce
  }

  function initFilterable(root) {
    root.querySelectorAll("select[data-filterable]:not([data-filter-bound])").forEach((sel) => {
      sel.dataset.filterBound = "1";
      const all = Array.from(sel.options).map((o) => ({ value: o.value, text: o.textContent }));
      const input = document.createElement("input");
      input.type = "search";
      input.placeholder = sel.dataset.filterable;
      input.className =
        "mb-2 block w-full rounded-lg border border-slate-300 bg-slate-50 px-3.5 py-2 text-sm placeholder-slate-400 " +
        "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/25";
      sel.parentNode.insertBefore(input, sel);
      input.addEventListener("input", () => {
        const q = input.value.toLocaleLowerCase("tr");
        const cur = sel.value;
        sel.innerHTML = "";
        all.forEach((o) => {
          if (o.value === "" || o.value === cur || o.text.toLocaleLowerCase("tr").includes(q)) sel.add(new Option(o.text, o.value));
        });
        sel.value = cur;
      });
    });
  }

  window.LotusCascade = {
    init(root) {
      root = root || document;
      initCascade(root);
      initFilterable(root);
    },
  };
  document.addEventListener("DOMContentLoaded", () => window.LotusCascade.init(document));
})();
