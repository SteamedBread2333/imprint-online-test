(function () {
  var tip = document.getElementById("graph-node-tip");
  if (!tip) return;

  function esc(s) {
    if (s == null || s === "") return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function row(label, value, valueClass) {
    if (value == null || value === "") return "";
    var cls = valueClass ? " class=\"" + valueClass + "\"" : "";
    return (
      "<dl><dt>" +
      esc(label) +
      "</dt><dd" +
      cls +
      ">" +
      esc(value) +
      "</dd></dl>"
    );
  }

  function renderTip(d) {
    var kind = d.kind === "document" ? "文档" : "规则";
    var rows = [];
    rows.push("<p class=\"gt-kicker\">" + esc(kind) + " · " + esc(d.label || d.id) + "</p>");
    if (d.kind === "rule") {
      rows.push(row("claim", d.claim, "gt-claim"));
      rows.push(row("用户原话", d.text, "gt-text"));
      rows.push(row("status", d.status));
      if (d.scope && d.scope.length) rows.push(row("scope", d.scope.join(", ")));
    } else {
      if (d.path) {
        rows.push(
          "<dl><dt>path</dt><dd><code>" + esc(d.path) + "</code></dd></dl>"
        );
      }
      rows.push(row("heading", d.heading));
    }
    if (d.id) rows.push("<p class=\"gt-id\"><code>" + esc(d.id) + "</code></p>");
    tip.innerHTML = rows.join("");
  }

  function place(ev) {
    var pad = 12;
    var x = ev.clientX + pad;
    var y = ev.clientY + pad;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
    var r = tip.getBoundingClientRect();
    if (r.right > window.innerWidth - 8) x = ev.clientX - r.width - pad;
    if (r.bottom > window.innerHeight - 8) y = ev.clientY - r.height - pad;
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = Math.max(8, y) + "px";
  }

  function show(ev, g) {
    var raw = g.getAttribute("data-node-tip");
    if (!raw) return;
    try {
      renderTip(JSON.parse(raw));
    } catch (e) {
      return;
    }
    g.classList.add("is-hot");
    tip.hidden = false;
    tip.classList.add("on");
    place(ev);
  }

  function hide(g) {
    if (g) g.classList.remove("is-hot");
    tip.classList.remove("on");
    tip.hidden = true;
  }

  document.querySelectorAll(".desk-graph-svg .d3-hit").forEach(function (hit) {
    var g = hit.parentElement;
    if (!g || !g.classList.contains("d3-node")) return;
    hit.addEventListener("mouseenter", function (ev) {
      show(ev, g);
    });
    hit.addEventListener("mousemove", place);
    hit.addEventListener("mouseleave", function () {
      hide(g);
    });
    hit.addEventListener("focus", function (ev) {
      show(ev, g);
    });
    hit.addEventListener("blur", function () {
      hide(g);
    });
  });
})();
