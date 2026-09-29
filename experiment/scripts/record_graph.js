/* Mini desk-style force graph for record.html (matches imprint desk edge kinds). */
(function () {
  const PALETTE = ["#e8c99a", "#7cb8e8", "#a8d4a0", "#d4a0c8", "#c8b890", "#90c8d4", "#d4c090"];
  const STATUS_BORDER = { active: "#e8c99a", dormant: "#7a736c", superseded: "#7aa0c8" };
  const graphs = window.RECORD_GRAPHS || {};

  function scopeColor(scope) {
    if (!scope || !scope.length) return "#e8c99a";
    const s = scope[0];
    if (s === "doc") return "#6ec4c0";
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    return PALETTE[(h >>> 0) % PALETTE.length];
  }

  function nodeRadius(n) {
    if (n.kind === "document") return 11;
    return n.status === "superseded" ? 10 : 14;
  }

  function shortLabel(n) {
    if (n.kind === "document") return n.label || n.path || n.id;
    return (n.label || n.id).slice(0, 14);
  }

  function mount(host) {
    const key = host.dataset.graph;
    const spec = graphs[key];
    if (!spec) return;

    const w = host.clientWidth || 520;
    const h = 280;
    const svg = d3.select(host).append("svg").attr("width", w).attr("height", h);
    const gRoot = svg.append("g");
    const gLinks = gRoot.append("g");
    const gNodes = gRoot.append("g");

    svg.append("defs").append("marker")
      .attr("id", "arrow-super-" + key)
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 14)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-4L8,0L0,4")
      .attr("fill", "#e07060");

    const nodes = spec.nodes.map(n => ({
      ...n,
      fill: n.kind === "document" ? "#1a2826" : scopeColor(n.scope),
      stroke: n.kind === "document" ? "#6ec4c0" : (STATUS_BORDER[n.status] || "#9a9084"),
      r: nodeRadius(n),
    }));
    const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
    const links = spec.edges
      .filter(e => byId[e.source] && byId[e.target])
      .map(e => ({ ...e, source: byId[e.source], target: byId[e.target] }));

    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(72).strength(0.55))
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(0, 0))
      .force("collide", d3.forceCollide().radius(d => d.r + 8));

    const zoom = d3.zoom().scaleExtent([0.4, 2.5]).on("zoom", ev => {
      gRoot.attr("transform", ev.transform);
    });
    svg.call(zoom);

    gLinks.selectAll("line")
      .data(links)
      .join("line")
      .attr("class", d => "d3-link " + d.kind)
      .attr("marker-end", d => d.kind === "supersedes" ? "url(#arrow-super-" + key + ")" : null);

    const ng = gNodes.selectAll("g.d3-node")
      .data(nodes)
      .join("g")
      .attr("class", d => "d3-node" + (d.kind === "document" ? " doc-node" : ""))
      .call(d3.drag()
        .on("start", (ev, d) => {
          if (!ev.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (ev, d) => {
          d.fx = ev.x;
          d.fy = ev.y;
        })
        .on("end", (ev, d) => {
          if (!ev.active) sim.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));

    ng.append("circle")
      .attr("r", d => d.r)
      .attr("fill", d => d.fill)
      .attr("stroke", d => d.stroke)
      .attr("stroke-width", d => (d.status === "superseded" ? 2.5 : 2));

    ng.append("text")
      .attr("class", "d3-label")
      .attr("dy", d => d.r + 11)
      .text(d => shortLabel(d));

    sim.on("tick", () => {
      gLinks.selectAll("line")
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      ng.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    sim.stop();
    for (let i = 0; i < 180; i++) sim.tick();
    sim.on("tick", null)();
    const b = gRoot.node().getBBox();
    const pad = 40;
    const k = Math.min(
      (w - pad) / (b.width || 1),
      (h - pad) / (b.height || 1),
      1.35
    );
    const tx = w / 2 - (b.x + b.width / 2) * k;
    const ty = h / 2 - (b.y + b.height / 2) * k;
    svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
  }

  document.querySelectorAll(".desk-graph-cy").forEach(mount);
})();
