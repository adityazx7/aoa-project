/**
 * =====================================================================
 * CAMPUS INDOOR / OUTDOOR NAVIGATOR (VIT BLUEPRINT) - CLIENT ENGINE
 * =====================================================================
 * Integrates 2D SVG with D3-Zoom, Fuse.js fuzzy search, Minimap,
 * Frontier Replay, Live Comparison Table, Directions, Three.js 3D View,
 * and Dev Graph Editor.
 */

(function () {
  const store = {
    graph: null,
    nodesMap: {},
    fuse: null,
    fromId: "",
    toId: "",
    selectionTarget: "auto",
    autoApply: true,
    viewMode: "c", // 'c', 'f1', 'f0', '3c', '3i', 'editor'
    routeData: null,
    activeAlgo: "dijkstra",
    options: {
      avoidStairs: false,
      stairsPenalty: 4.0,
      accessibleOnly: false,
      preferIndoor: false,
      kAlternatives: 1
    },
    replay: {
      active: false,
      step: 0,
      timer: null,
      speed: 1.0
    },
    threed: {
      renderer: null,
      scene: null,
      camera: null,
      controls: null,
      raf: null,
      explodeDist: 12.0,
      raycaster: null,
      mouse: null,
      clickableNodes: [],
      walkerMesh: null,
      walkerCurve: null,
      walkerProgress: 0.0
    },
    editor: {
      enabled: false,
      draggedNode: null,
      connectSource: null
    }
  };

  const LEVEL_NAMES = {
    c: "Campus Grounds",
    f1: "VIT Floor 1 (Walkway)",
    f0: "VIT Basement Labs"
  };

  const VIEWBOXES = {
    c: [0, 0, 1650, 930],
    f1: [0, 40, 1340, 720],
    f0: [0, 140, 1340, 510]
  };

  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  function initApp() {
    initTabs();
    initComboboxes();
    initDynamicSelectionControls();
    initShortcuts();
    initReplayControls();
    fetchCampusGraph();
  }

  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", initApp);
  } else {
    initApp();
  }

  async function fetchCampusGraph() {
    try {
      const res = await fetch("/api/campus/graph?t=" + Date.now());
      if (!res.ok) throw new Error("Failed to load campus graph");
      const data = await res.json();
      store.graph = data;
      store.nodesMap = {};
      data.nodes.forEach((n) => (store.nodesMap[n.id] = n));

      initFuse();
      render2D();
      renderMinimap();
      initUrlState();
    } catch (err) {
      console.error("[Campus Navigator]", err);
    }
  }

  // --- FUSE.JS FUZZY SEARCH COMBOBOXES ---
  function initFuse() {
    if (!window.Fuse || !store.graph) return;
    const items = store.graph.nodes
      .filter((n) => n.type !== "j")
      .map((n) => ({
        id: n.id,
        label: n.label,
        level: n.level,
        levelName: LEVEL_NAMES[n.level] || n.level,
        type: n.type
      }));

    store.fuse = new Fuse(items, {
      keys: ["label", "id", "levelName"],
      threshold: 0.35,
      minMatchCharLength: 1
    });

    populateDropdown("fromDropdown", "fromInput", (id) => setEndpoint("from", id));
    populateDropdown("toDropdown", "toInput", (id) => setEndpoint("to", id));
  }

  function populateDropdown(dropdownId, inputId, onSelect) {
    const dropdown = $(dropdownId);
    const input = $(inputId);
    if (!dropdown || !input) return;

    function renderList(items) {
      dropdown.innerHTML = "";
      if (items.length === 0) {
        dropdown.innerHTML = '<div style="padding: 10px; color: var(--c-mut); font-size: 0.8rem;">No matching locations</div>';
        dropdown.style.display = "block";
        return;
      }

      const groups = {};
      items.forEach((item) => {
        const lv = item.level;
        if (!groups[lv]) groups[lv] = [];
        groups[lv].push(item);
      });

      Object.keys(groups).forEach((lv) => {
        const title = document.createElement("div");
        title.className = "combobox-group-title";
        title.innerText = LEVEL_NAMES[lv] || lv;
        dropdown.appendChild(title);

        groups[lv].forEach((item) => {
          const row = document.createElement("div");
          row.className = "combobox-item";
          row.innerHTML = `<span>${item.label}</span> <span class="combobox-item-badge">${item.id}</span>`;
          row.onclick = () => {
            input.value = item.label;
            dropdown.style.display = "none";
            onSelect(item.id);
          };
          dropdown.appendChild(row);
        });
      });

      dropdown.style.display = "block";
    }

    input.addEventListener("focus", () => {
      const val = input.value.trim();
      if (!val) {
        renderList(
          store.graph.nodes
            .filter((n) => n.type !== "j")
            .map((n) => ({ id: n.id, label: n.label, level: n.level }))
        );
      } else if (store.fuse) {
        const results = store.fuse.search(val).map((r) => r.item);
        renderList(results);
      }
    });

    input.addEventListener("input", () => {
      const val = input.value.trim();
      if (!val) {
        renderList(
          store.graph.nodes
            .filter((n) => n.type !== "j")
            .map((n) => ({ id: n.id, label: n.label, level: n.level }))
        );
      } else if (store.fuse) {
        const results = store.fuse.search(val).map((r) => r.item);
        renderList(results);
      }
    });

    let activeIndex = -1;

    input.addEventListener("keydown", (e) => {
      const items = dropdown.querySelectorAll(".combobox-item");
      if (dropdown.style.display !== "block" || items.length === 0) {
        if (e.key === "ArrowDown") {
          input.dispatchEvent(new Event("focus"));
        }
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIndex = (activeIndex + 1) % items.length;
        items.forEach((it, idx) => it.classList.toggle("focused", idx === activeIndex));
        items[activeIndex]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIndex = (activeIndex - 1 + items.length) % items.length;
        items.forEach((it, idx) => it.classList.toggle("focused", idx === activeIndex));
        items[activeIndex]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (activeIndex >= 0 && items[activeIndex]) {
          items[activeIndex].click();
        }
      } else if (e.key === "Escape") {
        dropdown.style.display = "none";
        activeIndex = -1;
      }
    });

    document.addEventListener("click", (e) => {
      if (!dropdown.contains(e.target) && e.target !== input) {
        dropdown.style.display = "none";
        activeIndex = -1;
      }
    });
  }

  function setEndpoint(role, id) {
    if (role === "from") {
      store.fromId = id;
      if ($("fromInput")) $("fromInput").value = store.nodesMap[id]?.label || id;
    } else {
      store.toId = id;
      if ($("toInput")) $("toInput").value = store.nodesMap[id]?.label || id;
    }

    if (store.fromId && store.toId) {
      setDynamicStatus("solved", `Dynamic Route: <b>${store.nodesMap[store.fromId]?.label}</b> ➔ <b>${store.nodesMap[store.toId]?.label}</b> via ${store.activeAlgo.toUpperCase()}`);
      calculateCampusRoute();
    } else if (store.fromId) {
      setDynamicStatus("picking-dest", `Start set: <b>${store.nodesMap[store.fromId]?.label}</b>. Click target destination node on map.`);
      updateActiveHighlights();
    } else if (store.toId) {
      setDynamicStatus("picking-start", `Destination set: <b>${store.nodesMap[store.toId]?.label}</b>. Click origin node on map.`);
      updateActiveHighlights();
    }
  }

  function handleDynamicNodeSelection(id) {
    if (!id || !store.nodesMap[id]) return;
    const label = store.nodesMap[id]?.label || id;

    // 1. Explicit Pick Start Mode
    if (store.selectionTarget === "from") {
      store.fromId = id;
      if ($("fromInput")) $("fromInput").value = label;
      store.selectionTarget = "auto";
      updateSelectionButtons();
      if (store.toId && store.fromId !== store.toId) {
        setDynamicStatus("solved", `Dynamic Route: <b>${label}</b> ➔ <b>${store.nodesMap[store.toId]?.label}</b> (${store.activeAlgo.toUpperCase()})`);
        if (store.autoApply) calculateCampusRoute();
      } else {
        setDynamicStatus("picking-dest", `Start set: <b>${label}</b>. Now click destination node on map.`);
        updateActiveHighlights();
        render2D();
      }
      return;
    }

    // 2. Explicit Pick Destination Mode
    if (store.selectionTarget === "to") {
      store.toId = id;
      if ($("toInput")) $("toInput").value = label;
      store.selectionTarget = "auto";
      updateSelectionButtons();
      if (store.fromId && store.fromId !== store.toId) {
        setDynamicStatus("solved", `Dynamic Route: <b>${store.nodesMap[store.fromId]?.label}</b> ➔ <b>${label}</b> (${store.activeAlgo.toUpperCase()})`);
        if (store.autoApply) calculateCampusRoute();
      } else {
        setDynamicStatus("picking-start", `Destination set: <b>${label}</b>. Now click start node on map.`);
        updateActiveHighlights();
        render2D();
      }
      return;
    }

    // 3. Default Seamless Point-to-Point Auto Cycle
    if (!store.fromId || (store.fromId && store.toId)) {
      // Starting new pair: set Start
      store.fromId = id;
      store.toId = "";
      store.routeData = null;
      if ($("fromInput")) $("fromInput").value = label;
      if ($("toInput")) $("toInput").value = "";
      if ($("directionsList")) {
        $("directionsList").innerHTML =
          `<div style="padding: 20px; text-align: center; color: var(--c-mut); font-size: 0.82rem;">Start selected: <b>${label}</b>. Now click destination node on blueprint to compute path.</div>`;
      }
      setDynamicStatus("picking-dest", `Start point: <b>${label}</b>. Click destination node to apply ${store.activeAlgo.toUpperCase()} algorithm.`);
      updateActiveHighlights();
      render2D();
      if (store.viewMode === "3c" || store.viewMode === "3i") render3D(store.viewMode);
    } else if (store.fromId && !store.toId) {
      if (id === store.fromId) {
        setDynamicStatus("picking-dest", `Start point is <b>${label}</b>. Click a <i>different</i> node for destination.`);
        return;
      }
      // Set End and immediately apply algorithm
      store.toId = id;
      if ($("toInput")) $("toInput").value = label;
      setDynamicStatus("solved", `Applying algorithm: <b>${store.nodesMap[store.fromId]?.label}</b> ➔ <b>${label}</b> (${store.activeAlgo.toUpperCase()})...`);
      if (store.autoApply) {
        calculateCampusRoute();
      } else {
        updateActiveHighlights();
      }
    }
  }

  function setDynamicStatus(statusClass, htmlText) {
    const pill = $("dynamicStatusPill");
    const text = $("dynamicStatusText");
    if (pill) {
      pill.className = `dynamic-status-pill ${statusClass}`;
    }
    if (text) {
      text.innerHTML = htmlText;
    }
  }

  function updateSelectionButtons() {
    if ($("btnSetStartMode")) {
      $("btnSetStartMode").classList.toggle("active", store.selectionTarget === "from");
    }
    if ($("btnSetDestMode")) {
      $("btnSetDestMode").classList.toggle("active", store.selectionTarget === "to");
    }
  }

  function initDynamicSelectionControls() {
    if ($("btnSetStartMode")) {
      $("btnSetStartMode").onclick = () => {
        store.selectionTarget = store.selectionTarget === "from" ? "auto" : "from";
        updateSelectionButtons();
        if (store.selectionTarget === "from") {
          setDynamicStatus("picking-start", "Click any node on the blueprint to set <b>Start Point</b>.");
        } else {
          setDynamicStatus("idle", "Interactive Mode: Click any node to choose Start point.");
        }
      };
    }

    if ($("btnSetDestMode")) {
      $("btnSetDestMode").onclick = () => {
        store.selectionTarget = store.selectionTarget === "to" ? "auto" : "to";
        updateSelectionButtons();
        if (store.selectionTarget === "to") {
          setDynamicStatus("picking-dest", "Click any node on the blueprint to set <b>Destination Point</b>.");
        } else {
          setDynamicStatus("idle", "Interactive Mode: Click any node to choose Start point.");
        }
      };
    }

    if ($("btnAutoRouteMode")) {
      $("btnAutoRouteMode").onclick = () => {
        store.autoApply = !store.autoApply;
        $("btnAutoRouteMode").classList.toggle("active-state", store.autoApply);
        $("btnAutoRouteMode").innerText = store.autoApply ? "⚡ Auto-Apply Algorithm: ON" : "⏸ Auto-Apply Algorithm: OFF";
      };
    }
  }

  function clearEndpoint(role) {
    if (role === "from") {
      store.fromId = "";
      if ($("fromInput")) $("fromInput").value = "";
    } else {
      store.toId = "";
      if ($("toInput")) $("toInput").value = "";
    }
    store.routeData = null;
    if (!store.fromId && !store.toId) {
      clearSelection();
    } else if (store.fromId) {
      setDynamicStatus("picking-dest", `📍 Start set: <b>${store.nodesMap[store.fromId]?.label}</b>. Click destination on blueprint.`);
      updateActiveHighlights();
      render2D();
    } else {
      setDynamicStatus("picking-start", `🏁 Destination set: <b>${store.nodesMap[store.toId]?.label}</b>. Click start on blueprint.`);
      updateActiveHighlights();
      render2D();
    }
  }

  window.toggleRoutePreferences = function () {
    const drawer = document.getElementById("routePreferencesDrawer");
    const btn = document.getElementById("btnTogglePrefs");
    if (!drawer) return;
    const isHidden = drawer.style.display === "none";
    drawer.style.display = isHidden ? "block" : "none";
    if (btn) btn.classList.toggle("active", isHidden);
  };

  function initComboboxes() {
    if ($("btnSwapEndpoints")) {
      $("btnSwapEndpoints").onclick = () => {
        const temp = store.fromId;
        store.fromId = store.toId;
        store.toId = temp;

        if ($("fromInput")) $("fromInput").value = store.nodesMap[store.fromId]?.label || "";
        if ($("toInput")) $("toInput").value = store.nodesMap[store.toId]?.label || "";

        if (store.fromId && store.toId) {
          setDynamicStatus("solved", `Dynamic Route: <b>${store.nodesMap[store.fromId]?.label}</b> ➔ <b>${store.nodesMap[store.toId]?.label}</b> (${store.activeAlgo.toUpperCase()})`);
          calculateCampusRoute();
        } else {
          updateActiveHighlights();
        }
      };
    }
  }

  // --- SHORTCUTS (NEAREST ENTRANCE, STAIRS, LIFT) ---
  function initShortcuts() {
    $$(".shortcut-chip").forEach((chip) => {
      chip.onclick = async () => {
        const type = chip.dataset.shortcut || chip.dataset.type;
        const current = store.fromId || store.toId || "GATE";

        try {
          const res = await fetch(`/api/campus/shortcuts?node_id=${current}`);
          if (!res.ok) return;
          const data = await res.json();
          let target = null;
          if (type === "entrance") target = data.nearest_entrance;
          else if (type === "stairs") target = data.nearest_stairs;
          else if (type === "lift") target = data.nearest_lift;

          if (target) {
            store.fromId = current;
            store.toId = target.id;
            if ($("fromInput")) $("fromInput").value = store.nodesMap[store.fromId]?.label || store.fromId;
            if ($("toInput")) $("toInput").value = target.label;
            calculateCampusRoute();
          }
        } catch (e) {
          console.error(e);
        }
      };
    });
  }

  // --- TABS & LEVEL SWITCHING ---
  function initTabs() {
    $$(".campus-tab-btn").forEach((btn) => {
      btn.onclick = () => {
        $$(".campus-tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const mode = btn.dataset.tab || btn.dataset.view || "c";
        store.viewMode = mode;
        handleViewModeChange();
      };
    });

    if ($("campusAlgoSelect")) {
      $("campusAlgoSelect").onchange = (e) => {
        store.activeAlgo = e.target.value;
        if (store.fromId && store.toId) calculateCampusRoute();
      };
    }

    if ($("chkAvoidStairs")) {
      $("chkAvoidStairs").onchange = (e) => {
        store.options.avoidStairs = e.target.checked;
        if (store.fromId && store.toId) calculateCampusRoute();
      };
    }
    if ($("chkAccessibleOnly")) {
      $("chkAccessibleOnly").onchange = (e) => {
        store.options.accessibleOnly = e.target.checked;
        if (store.fromId && store.toId) calculateCampusRoute();
      };
    }
    if ($("chkPreferIndoor")) {
      $("chkPreferIndoor").onchange = (e) => {
        store.options.preferIndoor = e.target.checked;
        if (store.fromId && store.toId) calculateCampusRoute();
      };
    }
    if ($("chkAlternatives")) {
      $("chkAlternatives").onchange = (e) => {
        store.options.kAlternatives = e.target.checked ? 3 : 1;
        if (store.fromId && store.toId) calculateCampusRoute();
      };
    }

    if ($("btnCampusClear")) $("btnCampusClear").onclick = clearSelection;
    if ($("btnCampusRun")) $("btnCampusRun").onclick = calculateCampusRoute;

    if ($("btnSwapEndpoints")) {
      $("btnSwapEndpoints").onclick = () => {
        if (!store.fromId && !store.toId) return;
        const tmp = store.fromId;
        store.fromId = store.toId;
        store.toId = tmp;
        if ($("fromInput")) $("fromInput").value = store.nodesMap[store.fromId]?.label || "";
        if ($("toInput")) $("toInput").value = store.nodesMap[store.toId]?.label || "";
        updateActiveHighlights();
        if (store.fromId && store.toId) {
          calculateCampusRoute();
        } else {
          render2D();
        }
      };
    }

    if ($("btnShareRoute")) {
      $("btnShareRoute").onclick = () => {
        updateUrlState();
        if (navigator.clipboard) {
          navigator.clipboard.writeText(window.location.href).then(() => {
            showToast("🔗 Shareable route link copied to clipboard!");
          }).catch(() => {
            showToast("Copied: " + window.location.href);
          });
        } else {
          showToast("Route link: " + window.location.href);
        }
      };
    }
  }

  function showToast(msg) {
    const existing = document.querySelector(".toast-bubble");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast-bubble";
    toast.innerText = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  function initUrlState() {
    const params = new URLSearchParams(window.location.search);
    const from = params.get("from");
    const to = params.get("to");
    const algo = params.get("algo");
    const avoidStairs = params.get("avoid_stairs");
    const accessible = params.get("accessible");
    const indoor = params.get("indoor");

    if (algo && $("campusAlgoSelect")) {
      $("campusAlgoSelect").value = algo;
      store.activeAlgo = algo;
    }
    if (avoidStairs !== null && $("chkAvoidStairs")) {
      $("chkAvoidStairs").checked = (avoidStairs === "true");
      store.options.avoidStairs = (avoidStairs === "true");
    }
    if (accessible !== null && $("chkAccessibleOnly")) {
      $("chkAccessibleOnly").checked = (accessible === "true");
      store.options.accessibleOnly = (accessible === "true");
    }
    if (indoor !== null && $("chkPreferIndoor")) {
      $("chkPreferIndoor").checked = (indoor === "true");
      store.options.preferIndoor = (indoor === "true");
    }

    if (from && store.nodesMap[from]) {
      store.fromId = from;
      if ($("fromInput")) $("fromInput").value = store.nodesMap[from].label;
    }
    if (to && store.nodesMap[to]) {
      store.toId = to;
      if ($("toInput")) $("toInput").value = store.nodesMap[to].label;
    }

    if (store.fromId && store.toId) {
      calculateCampusRoute();
    }
  }

  function updateUrlState() {
    if (store.fromId && store.toId) {
      const params = new URLSearchParams();
      params.set("from", store.fromId);
      params.set("to", store.toId);
      params.set("algo", store.activeAlgo);
      if (store.options.avoidStairs) params.set("avoid_stairs", "true");
      if (store.options.accessibleOnly) params.set("accessible", "true");
      if (store.options.preferIndoor) params.set("indoor", "true");
      window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
    }
  }

  function handleViewModeChange() {
    const is3D = store.viewMode && store.viewMode.startsWith("3");
    const isEditor = store.viewMode === "editor";
    const isExploded = store.viewMode === "3f";

    if ($("campusSvgContainer")) $("campusSvgContainer").style.display = is3D ? "none" : "block";
    if ($("campus3DContainer")) $("campus3DContainer").style.display = is3D ? "block" : "none";
    if ($("campusMinimapBox")) $("campusMinimapBox").style.display = is3D ? "none" : "block";
    if ($("editorDrawer")) $("editorDrawer").style.display = isEditor ? "block" : "none";
    if ($("threedExplodeOverlay")) $("threedExplodeOverlay").style.display = isExploded ? "flex" : "none";

    store.editor.enabled = isEditor;

    if (is3D) {
      init3D();
      if (store.threed.renderer && store.threed.camera) {
        const container = $("campus3DContainer");
        const w = container.clientWidth || (container.parentElement ? container.parentElement.clientWidth : 1000) || 1000;
        const h = 540;
        store.threed.renderer.setSize(w, h);
        store.threed.camera.aspect = w / h;
        store.threed.camera.updateProjectionMatrix();
      }
      render3D(store.viewMode);
    } else {
      if (store.threed.raf) cancelAnimationFrame(store.threed.raf);
      render2D();
      renderMinimap();
    }
  }

  function clearSelection() {
    store.fromId = "";
    store.toId = "";
    store.routeData = null;
    store.selectionTarget = "auto";
    updateSelectionButtons();
    setDynamicStatus("idle", "Interactive Point-to-Point Mode: Click any node on the blueprint to set <b>Start Point</b>.");
    if ($("fromInput")) $("fromInput").value = "";
    if ($("toInput")) $("toInput").value = "";
    if ($("directionsList")) {
      $("directionsList").innerHTML =
        '<div style="text-align: center; color: var(--c-mut); padding: 20px; font-size: 0.84rem;">Select origin and destination to generate step-by-step turn guidance.</div>';
    }
    if ($("frontierStepperBar")) $("frontierStepperBar").style.display = "none";
    if ($("comparisonTableBody")) {
      $("comparisonTableBody").innerHTML =
        '<tr><td colspan="6" style="text-align:center; padding: 18px; color: var(--c-mut);">No active query comparison.</td></tr>';
    }
    updateActiveHighlights();
    render2D();
    if (store.viewMode === "3c" || store.viewMode === "3i") render3D(store.viewMode);
  }

  // --- ROUTE CALCULATION (API) ---
  async function calculateCampusRoute() {
    if (!store.fromId || !store.toId) {
      alert("Please select both Origin and Destination locations.");
      return;
    }
    if (store.fromId === store.toId) {
      alert("Origin and Destination cannot be the same location.");
      return;
    }

    try {
      const res = await fetch("/api/campus/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: store.fromId,
          destination: store.toId,
          algorithm: store.activeAlgo,
          avoid_stairs: store.options.avoidStairs,
          stairs_penalty: store.options.stairsPenalty,
          accessible_only: store.options.accessibleOnly,
          prefer_indoor: store.options.preferIndoor,
          k_alternatives: store.options.kAlternatives
        })
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Route could not be calculated.");
        return;
      }

      const data = await res.json();
      store.routeData = data;

      const fromNode = store.nodesMap[store.fromId];
      const toNode = store.nodesMap[store.toId];
      if (
        fromNode &&
        toNode &&
        fromNode.level === toNode.level &&
        store.viewMode &&
        !store.viewMode.startsWith("3") &&
        store.viewMode !== "editor"
      ) {
        store.viewMode = fromNode.level;
        $$(".campus-tab-btn").forEach((b) =>
          b.classList.toggle("active", (b.dataset.tab || b.dataset.view) === store.viewMode)
        );
      }

      render2D();
      renderMinimap();
      updateDirections(data);
      updateComparisonTable(data.comparison);
      setupReplay(data.primary.visitedOrder);
      updateUrlState();

      // Auto-fit view to calculated route
      if (data.primary && data.primary.path) {
        fitToBounds(data.primary.path);
      }

      if (store.viewMode && store.viewMode.startsWith("3")) {
        render3D(store.viewMode);
      }
    } catch (e) {
      console.error(e);
    }
  }

  // --- 2D RENDERING (SVG + D3-ZOOM + POLYLINE ROUTES) ---
  function render2D() {
    if (!store.graph) return;
    const svgEl = $("campusSvg");
    if (!svgEl) return;

    const level = store.viewMode === "editor" ? "c" : (store.viewMode || "c");
    if (level.startsWith("3")) return;

    const vb = VIEWBOXES[level] || VIEWBOXES.c;
    svgEl.setAttribute("viewBox", vb.join(" "));

    let html = '<g id="zoomGroup">';

    // 1. Rooms with clamped internal labels
    store.graph.rooms
      .filter((r) => r.level === level)
      .forEach((r) => {
        const rx = r.kind === "bridge" || r.kind === "stair" ? 10 : 6;
        html += `<rect class="r k_${r.kind}" x="${r.x}" y="${r.y}" width="${r.width}" height="${r.height}" rx="${rx}"/>`;
        if (r.label) {
          const fs = Math.max(10, Math.min(level === "c" ? 16 : 14, r.width / 6.2, r.height / 2.2));
          const maxChars = Math.max(3, Math.floor((r.width - 10) / (fs * 0.54)));
          const truncated = r.label.length > maxChars ? r.label.slice(0, maxChars - 1) + "…" : r.label;
          html += `<text class="r-label" x="${r.x + r.width / 2}" y="${r.y + r.height / 2 + fs / 2.6}" font-size="${fs}" text-anchor="middle">
            <title>${r.label}</title>
            ${truncated}
          </text>`;
        }
      });

    // 2. Base Edges
    store.graph.edges.forEach((e) => {
      const na = store.nodesMap[e.a];
      const nb = store.nodesMap[e.b];
      if (!na || !nb) return;
      if (na.level !== level || nb.level !== level) return;

      html += `<line class="e ${e.type}" data-a="${e.a}" data-b="${e.b}" x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}">
        <title>${e.kind || e.type} | Cost: ${(e.time_s || e.cost || 0).toFixed(1)}s</title>
      </line>`;
    });

    // 2b. Active Route: Solid on active level, ghosted on other levels!
    if (store.routeData && store.routeData.primary && store.routeData.primary.path) {
      const p = store.routeData.primary.path;
      for (let i = 0; i < p.length - 1; i++) {
        const na = store.nodesMap[p[i]];
        const nb = store.nodesMap[p[i + 1]];
        if (!na || !nb) continue;

        const onCurrentLevel = (na.level === level && nb.level === level);
        if (onCurrentLevel) {
          html += `<line class="path-line path-animated" x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}"/>`;
        } else if (na.level !== "c" && level !== "c") {
          // Ghosted overview between interior floors
          html += `<line class="path-line-ghosted" x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}"/>`;
        }

        // Portal transition chips
        if ((na.level === level && nb.level !== level) || (nb.level === level && na.level !== level)) {
          const currentEnd = na.level === level ? na : nb;
          const otherEnd = na.level === level ? nb : na;
          const icon = (na.type === "l" || nb.type === "l") ? "🛗" : "🪜";
          const destName = LEVEL_NAMES[otherEnd.level] || otherEnd.level;
          html += `
            <g class="portal-chip-marker" transform="translate(${currentEnd.x}, ${currentEnd.y - 18})">
              <rect x="-48" y="-11" width="96" height="22" rx="11" fill="var(--c-card)" stroke="var(--c-acc)" stroke-width="1.8" />
              <text class="portal-chip-text" x="0" y="4">${icon} ${destName}</text>
            </g>
          `;
        }
      }
    }

    // 3. Nodes: Hide junctions unless in Dev Editor
    store.graph.nodes
      .filter((n) => n.level === level)
      .forEach((n) => {
        if (n.type === "j" && !store.editor.enabled) return;

        let cls = `n ${n.type}`;
        if (n.id === store.fromId) cls += " fr";
        else if (n.id === store.toId) cls += " to";
        else if (store.routeData && store.routeData.primary && store.routeData.primary.path.includes(n.id)) {
          cls += " on";
        }

        const isTerminal = (n.id === store.fromId || n.id === store.toId);
        const r = isTerminal ? 11 : n.type === "j" ? 4 : 8;

        html += `<circle class="${cls}" data-id="${n.id}" cx="${n.x}" cy="${n.y}" r="${r}">
          <title>${n.label} (${n.id})</title>
        </circle>`;

        // Terminal markers
        if (n.id === store.fromId) {
          html += `
            <g transform="translate(${n.x}, ${n.y - 20})">
              <rect x="-24" y="-10" width="48" height="18" rx="9" fill="#059669" />
              <text x="0" y="3" fill="#ffffff" font-size="10" font-weight="700" text-anchor="middle">START</text>
            </g>
          `;
        } else if (n.id === store.toId) {
          html += `
            <g transform="translate(${n.x}, ${n.y - 20})">
              <rect x="-20" y="-10" width="40" height="18" rx="9" fill="#dc2626" />
              <text x="0" y="3" fill="#ffffff" font-size="10" font-weight="700" text-anchor="middle">END</text>
            </g>
          `;
        }
      });

    html += "</g>";

    // Read current zoom transform BEFORE rebuilding SVG so view stays rock-solid
    let currentTransform = null;
    if (window.d3 && svgEl) {
      try {
        currentTransform = d3.zoomTransform(svgEl);
      } catch (e) {}
    }

    svgEl.innerHTML = html;

    // Node click & pointer selection handler (forgiving of tiny hand drift)
    svgEl.querySelectorAll("circle.n").forEach((c) => {
      let startPos = null;
      c.onpointerdown = (e) => {
        startPos = { x: e.clientX, y: e.clientY };
      };
      c.onpointerup = (e) => {
        if (!startPos) return;
        const dist = Math.hypot(e.clientX - startPos.x, e.clientY - startPos.y);
        startPos = null;
        if (dist <= 8) {
          e.stopPropagation();
          const id = c.dataset.id;
          if (store.editor.enabled) {
            handleEditorNodeClick(id);
          } else {
            handleDynamicNodeSelection(id);
          }
        }
      };
      c.onclick = (e) => {
        e.stopPropagation();
        const id = c.dataset.id;
        if (store.editor.enabled) {
          handleEditorNodeClick(id);
        } else {
          handleDynamicNodeSelection(id);
        }
      };
    });

    // D3 Zoom & Pan (Nodes remain completely static)
    if (window.d3) {
      const svgSel = d3.select(svgEl);
      store.zoomBehavior = d3
        .zoom()
        .scaleExtent([0.3, 4.5])
        .filter((event) => !store.editor.enabled || event.type !== "mousedown")
        .on("zoom", (event) => {
          d3.select("#zoomGroup").attr("transform", event.transform);
          updateMinimap(event.transform, vb);
        });
      svgSel.call(store.zoomBehavior);

      // Re-apply preserved zoom/pan transform so the node/view never jumps away on selection
      if (currentTransform && (currentTransform.k !== 1 || currentTransform.x !== 0 || currentTransform.y !== 0)) {
        d3.select("#zoomGroup").attr("transform", currentTransform);
        updateMinimap(currentTransform, vb);
      }

      if ($("btnZoomReset")) {
        $("btnZoomReset").onclick = () => {
          if (store.routeData && store.routeData.primary && store.routeData.primary.path) {
            fitToBounds(store.routeData.primary.path);
          } else {
            fitToBounds([]);
          }
        };
      }

      // ONLY attach node drag behavior when Dev Editor is explicitly active
      if (store.editor.enabled) {
        d3.selectAll("circle.n").call(
          d3.drag().on("drag", function (event) {
            const id = this.dataset.id;
            const n = store.nodesMap[id];
            if (n) {
              n.x = Math.round(event.x);
              n.y = Math.round(event.y);
              d3.select(this).attr("cx", n.x).attr("cy", n.y);
              d3.selectAll(`line.e[data-a="${id}"]`).attr("x1", n.x).attr("y1", n.y);
              d3.selectAll(`line.e[data-b="${id}"]`).attr("x2", n.x).attr("y2", n.y);
            }
          })
        );
      }
    }
  }

  // --- FIT TO BOUNDS (AUTO-FRAME WITH 10% PADDING) ---
  function fitToBounds(nodesList, padding = 0.12) {
    const svgEl = $("campusSvg");
    if (!svgEl || !window.d3 || !store.zoomBehavior) return;

    const level = store.viewMode === "editor" ? "c" : (store.viewMode || "c");
    const vb = VIEWBOXES[level] || VIEWBOXES.c;

    let targetNodes = [];
    if (nodesList && nodesList.length > 0) {
      targetNodes = nodesList
        .map((id) => store.nodesMap[id])
        .filter((n) => n && n.level === level);
    }
    if (targetNodes.length === 0) {
      targetNodes = store.graph.nodes.filter((n) => n.level === level);
    }
    if (targetNodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    targetNodes.forEach((n) => {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    });

    const w = Math.max(maxX - minX, 120);
    const h = Math.max(maxY - minY, 120);
    const padX = w * padding + 40;
    const padY = h * padding + 40;

    const bboxW = w + 2 * padX;
    const bboxH = h + 2 * padY;

    const k = Math.min(vb[2] / bboxW, vb[3] / bboxH, 2.5);
    const tx = (vb[2] - (minX + maxX) * k) / 2;
    const ty = (vb[3] - (minY + maxY) * k) / 2;

    const svgSel = d3.select(svgEl);
    const zoomTransform = d3.zoomIdentity.translate(tx, ty).scale(k);
    svgSel.transition().duration(500).call(store.zoomBehavior.transform, zoomTransform);
  }

  function handleEditorNodeClick(id) {
    if (!store.editor.connectSource) {
      store.editor.connectSource = id;
      alert(`Selected node '${id}'. Now click a second node to toggle an edge between them.`);
    } else {
      const a = store.editor.connectSource;
      const b = id;
      store.editor.connectSource = null;
      if (a === b) return;

      const idx = store.graph.edges.findIndex(
        (e) => (e.a === a && e.b === b) || (e.a === b && e.b === a)
      );

      if (idx >= 0) {
        store.graph.edges.splice(idx, 1);
        alert(`Removed edge ${a} - ${b}`);
      } else {
        const na = store.nodesMap[a];
        const nb = store.nodesMap[b];
        const dist = Math.hypot(na.x - nb.x, na.y - nb.y);
        const cost = Math.round(dist * (na.level === "c" ? 0.25 : 0.1) * 10) / 10;
        store.graph.edges.push({
          a,
          b,
          type: "w",
          cost: cost || 1.0,
          accessible: true,
          outdoor: na.level === "c"
        });
        alert(`Added edge ${a} - ${b} (cost ${cost}m)`);
      }
      render2D();
    }
  }

  function updateActiveHighlights() {
    $$("circle.n").forEach((c) => {
      const id = c.dataset.id;
      c.classList.remove("fr", "to", "on");
      if (id === store.fromId) c.classList.add("fr");
      if (id === store.toId) c.classList.add("to");
    });
  }

  // --- MINIMAP (CLEAN SCALED SVG RADAR) ---
  function renderMinimap() {
    const mini = $("campusMinimap");
    if (!mini || !store.graph) return;
    const level = store.viewMode === "editor" ? "c" : store.viewMode;
    if (level && level.startsWith("3")) return;

    const vb = VIEWBOXES[level] || VIEWBOXES.c;
    mini.setAttribute("viewBox", vb.join(" "));

    let h = "";
    // Draw rooms
    store.graph.rooms
      .filter((r) => r.level === level)
      .forEach((r) => {
        h += `<rect fill="rgba(148, 163, 184, 0.4)" rx="3" x="${r.x}" y="${r.y}" width="${r.width}" height="${r.height}"/>`;
      });

    // Draw active route on minimap
    if (store.routeData && store.routeData.primary && store.routeData.primary.path) {
      const p = store.routeData.primary.path;
      for (let i = 0; i < p.length - 1; i++) {
        const na = store.nodesMap[p[i]];
        const nb = store.nodesMap[p[i + 1]];
        if (na && nb && na.level === level && nb.level === level) {
          h += `<line x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}" stroke="#ea580c" stroke-width="12" stroke-linecap="round"/>`;
        }
      }
    }

    // Viewport bounding box
    h += `<rect id="minimapViewport" class="minimap-viewport-rect" x="${vb[0]}" y="${vb[1]}" width="${vb[2]}" height="${vb[3]}" rx="4"/>`;
    mini.innerHTML = h;
  }

  function updateMinimap(transform, vb) {
    const rect = $("minimapViewport");
    if (!rect) return;
    const k = transform.k || 1;
    const w = vb[2] / k;
    const h = vb[3] / k;
    const x = vb[0] - transform.x / k;
    const y = vb[1] - transform.y / k;

    rect.setAttribute("x", x);
    rect.setAttribute("y", y);
    rect.setAttribute("width", w);
    rect.setAttribute("height", h);
  }

  // --- REPLAY CONTROLS ---
  function initReplayControls() {
    if ($("btnPlayPause")) $("btnPlayPause").onclick = togglePlay;
    if ($("btnStepForward")) $("btnStepForward").onclick = () => stepReplay(1);
    if ($("btnStepBack")) $("btnStepBack").onclick = () => stepReplay(-1);
    if ($("replaySpeedSelect")) {
      $("replaySpeedSelect").onchange = (e) => {
        store.replay.speed = parseFloat(e.target.value);
        if (store.replay.active) {
          clearInterval(store.replay.timer);
          startPlayTimer();
        }
      };
    }
    if ($("replaySlider")) {
      $("replaySlider").oninput = (e) => {
        pausePlay();
        store.replay.step = parseInt(e.target.value);
        renderReplayStep();
      };
    }
  }

  function setupReplay(visitedOrder) {
    if (!visitedOrder || visitedOrder.length === 0) return;
    $("frontierStepperBar").style.display = "flex";
    store.replay.step = 0;
    store.replay.active = false;
    $("replaySlider").max = visitedOrder.length - 1;
    $("replaySlider").value = 0;
    $("btnPlayPause").innerText = "▶";
    renderReplayStep();
  }

  function togglePlay() {
    if (store.replay.active) pausePlay();
    else startPlay();
  }

  function startPlay() {
    store.replay.active = true;
    $("btnPlayPause").innerText = "⏸";
    startPlayTimer();
  }

  function pausePlay() {
    store.replay.active = false;
    $("btnPlayPause").innerText = "▶";
    clearInterval(store.replay.timer);
  }

  function startPlayTimer() {
    const order = store.routeData?.primary?.visitedOrder || [];
    const intervalMs = 250 / store.replay.speed;
    store.replay.timer = setInterval(() => {
      if (store.replay.step < order.length - 1) {
        store.replay.step++;
        renderReplayStep();
      } else {
        pausePlay();
      }
    }, intervalMs);
  }

  function stepReplay(delta) {
    pausePlay();
    const order = store.routeData?.primary?.visitedOrder || [];
    const target = Math.max(0, Math.min(order.length - 1, store.replay.step + delta));
    store.replay.step = target;
    renderReplayStep();
  }

  function renderReplayStep() {
    const order = store.routeData?.primary?.visitedOrder || [];
    if (order.length === 0) return;

    $("replaySlider").value = store.replay.step;
    const currId = order[store.replay.step];
    const node = store.nodesMap[currId];
    $("replayDesc").innerText = `Step ${store.replay.step + 1}/${order.length}: Settle '${node?.label || currId}'`;

    $$("circle.n").forEach((c) => {
      const id = c.dataset.id;
      c.classList.remove("frontier");
      if (id === currId) c.classList.add("frontier");
    });
  }

  // --- TURN-BY-TURN GUIDANCE & BENCHMARK COMPARISON ---
  function updateDirections(data) {
    const list = $("directionsList");
    if (!list) return;

    const distM = data.total_m || data.primary?.total_m || 0;
    const timeS = data.total_s || data.primary?.total_s || data.estimatedSeconds || 0;

    if ($("totalDistanceBadge")) $("totalDistanceBadge").innerText = `${distM.toFixed(1)} m`;

    const mins = Math.floor(timeS / 60);
    const secs = Math.round(timeS % 60);
    if ($("estimatedTimeBadge")) {
      $("estimatedTimeBadge").innerText = mins > 0 ? `~${mins} min ${secs}s` : `~${secs}s walk`;
    }

    let html = "";
    const legs = (data.legs && data.legs.length > 0) ? data.legs : (data.directions || []);

    legs.forEach((leg) => {
      const icon = (leg.type === "stairs" || leg.edge_type === "s") ? "🪜" :
                   (leg.type === "lift" || leg.edge_type === "l") ? "🛗" :
                   (leg.type === "door" || leg.edge_type === "d") ? "🚪" :
                   (leg.type === "bridge" || leg.edge_type === "b") ? "🌉" : "🚶‍♂️";

      const lvName = LEVEL_NAMES[leg.level] || (leg.level === "f1" ? "Floor 1 Walkway" : leg.level === "f0" ? "Basement Labs" : "Campus Grounds");
      const instr = leg.instructions || leg.instruction || "Proceed along corridor";
      const lm = leg.landmark ? `📍 Near ${leg.landmark}` : "";
      const distStr = leg.distance_m ? `${leg.distance_m.toFixed(1)}m` : (leg.cost ? `${leg.cost.toFixed(1)}m` : "");
      const timeStr = leg.time_s ? `~${Math.round(leg.time_s)}s` : "";
      const pathAttr = JSON.stringify(leg.path || []).replace(/"/g, '&quot;');

      html += `
        <div class="turn-leg-card" onclick="CampusNavigator.focusLeg('${leg.level}', ${pathAttr})">
          <div class="turn-icon-badge">${icon}</div>
          <div class="turn-content">
            <div class="turn-title">${instr}</div>
            <div class="turn-meta">
              <span class="combobox-item-badge">${lvName}</span>
              ${distStr ? `<span>${distStr}</span>` : ""}
              ${timeStr ? `<span>${timeStr}</span>` : ""}
              ${lm ? `<span style="color: var(--c-acc); font-weight: 500;">${lm}</span>` : ""}
            </div>
          </div>
        </div>
      `;
    });

    // Quantum Cybersecurity & Blockchain Audit Seal
    html += `
      <div style="margin-top: 14px; padding: 12px 14px; background: rgba(59, 130, 246, 0.08); border: 1px dashed var(--c-acc); border-radius: 8px; font-size: 0.82rem; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="font-weight: 700; color: var(--c-ink);">🛡️ Quantum Digital Signature (QDS)</div>
          <div style="font-size: 0.74rem; color: var(--c-mut);">Sign route clearance via Teleportation & Bell Entanglement</div>
        </div>
        <button type="button" class="route-ghost-btn" onclick="CampusNavigator.signCurrentRouteQDS()" style="font-size: 0.76rem; padding: 6px 12px; font-weight: 600;">
          Sign Route
        </button>
      </div>
      <div id="qdsRouteSignatureBadge" style="display: none; margin-top: 8px; padding: 10px; background: rgba(16, 185, 129, 0.12); border: 1px solid #10b981; border-radius: 6px; font-size: 0.78rem; color: #059669; font-weight: 600;"></div>
    `;

    list.innerHTML = html;
  }

  async function signCurrentRouteQDS() {
    if (!store.fromId || !store.toId) return;
    const fromLabel = store.nodesMap[store.fromId]?.label || store.fromId;
    const toLabel = store.nodesMap[store.toId]?.label || store.toId;
    const msg = `Campus Transit Route Clearance: ${fromLabel} ➔ ${toLabel} via ${store.activeAlgo.toUpperCase()}`;
    
    try {
      const res = await fetch("/api/qds/simulate-attack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, attack_type: "none" })
      });
      if (res.ok) {
        const data = await res.json();
        const badge = $("qdsRouteSignatureBadge");
        if (badge) {
          badge.style.display = "block";
          badge.innerHTML = `✅ Route QDS Verified & Mined on Quantum Ledger (Block #${data.blockchain_receipt.block_index} | Hash: <code>${data.blockchain_receipt.block_hash.slice(0, 16)}...</code>)`;
        }
      }
    } catch (e) {
      console.error(e);
    }
  }

  function focusLeg(level, path) {
    if (level && level !== store.viewMode && !level.startsWith("3")) {
      store.viewMode = level;
      $$(".campus-tab-btn").forEach((b) =>
        b.classList.toggle("active", (b.dataset.tab || b.dataset.view) === level)
      );
      handleViewModeChange();
    }
    if (path && path.length > 0) {
      setTimeout(() => fitToBounds(path, 0.2), 50);
    }
  }

  function updateComparisonTable(comparison) {
    const tbody = $("comparisonTableBody");
    if (!tbody || !comparison) return;

    let h = "";
    comparison.forEach((row) => {
      const costStr = row.total_s !== undefined ? `${row.total_s.toFixed(1)}s` : `${row.cost.toFixed(1)}s`;
      h += `
        <tr>
          <td style="font-weight: 600;">${row.name}</td>
          <td style="font-family: 'JetBrains Mono', monospace; color: var(--c-path); font-weight: 600;">${costStr}</td>
          <td style="font-family: 'JetBrains Mono', monospace;">${row.nodesExpanded}</td>
          <td style="font-family: 'JetBrains Mono', monospace;">${row.timeMs} ms</td>
          <td><code style="font-size: 0.74rem;">${row.complexity}</code></td>
        </tr>
      `;
    });
    tbody.innerHTML = h;
  }

  // --- THREE.JS 3D ENGINE ---
  function init3D() {
    const container = $("campus3DContainer");
    if (!container || store.threed.renderer) return;

    const w = container.clientWidth || 800;
    const h = 580;

    const ren = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    ren.setSize(w, h);
    ren.setPixelRatio(window.devicePixelRatio || 1);
    container.appendChild(ren.domElement);

    const scene = new THREE.Scene();
    const isDark = document.documentElement.dataset.theme === "dark" || matchMedia("(prefers-color-scheme: dark)").matches;
    scene.background = new THREE.Color(isDark ? 0x0f172a : 0xf1f5f9);

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    camera.position.set(45, 65, 80);

    const controls = new THREE.OrbitControls(camera, ren.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(35, 5, 25);

    // Soft Hemisphere + Directional lighting
    const hemi = new THREE.HemisphereLight(0xffffff, 0x334155, 0.75);
    scene.add(hemi);
    const dir = new THREE.DirectionalLight(0xffffff, 0.7);
    dir.position.set(60, 120, 50);
    scene.add(dir);

    store.threed.renderer = ren;
    store.threed.scene = scene;
    store.threed.camera = camera;
    store.threed.controls = controls;

    if (typeof THREE !== "undefined") {
      if (!store.threed.raycaster) store.threed.raycaster = new THREE.Raycaster();
      if (!store.threed.mouse) store.threed.mouse = new THREE.Vector2();
    }

    ren.domElement.addEventListener("click", (e) => {
      if (!store.threed.raycaster || !store.threed.mouse) return;
      const rect = ren.domElement.getBoundingClientRect();
      store.threed.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      store.threed.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      store.threed.raycaster.setFromCamera(store.threed.mouse, camera);
      const hits = store.threed.raycaster.intersectObjects(store.threed.clickableNodes);
      if (hits.length > 0) {
        const id = hits[0].object.userData.nodeId;
        handleDynamicNodeSelection(id);
      }
    });

    if ($("threedExplodeSlider")) {
      $("threedExplodeSlider").oninput = (e) => {
        store.threed.explodeDist = parseFloat(e.target.value);
        if ($("explodeValBadge")) $("explodeValBadge").innerText = `${store.threed.explodeDist.toFixed(0)}m`;
        render3D(store.viewMode);
      };
    }
  }

  function makeTextSprite(message, bgColor = "rgba(15, 23, 42, 0.85)") {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    ctx.fillStyle = bgColor;
    if (ctx.roundRect) ctx.roundRect(8, 8, 240, 48, 10);
    else ctx.fillRect(8, 8, 240, 48);
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 18px -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(message, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(6.5, 1.6, 1);
    return sprite;
  }

  function setCameraPreset(preset) {
    if (!store.threed.camera || !store.threed.controls) return;
    const cam = store.threed.camera;
    const ctrl = store.threed.controls;

    if (preset === "top") {
      cam.position.set(35, 120, 25);
      ctrl.target.set(35, 0, 25);
    } else if (preset === "route" && store.threed.routeCenter) {
      cam.position.set(store.threed.routeCenter.x + 20, store.threed.routeCenter.y + 35, store.threed.routeCenter.z + 40);
      ctrl.target.copy(store.threed.routeCenter);
    } else {
      // Overview
      cam.position.set(45, 65, 80);
      ctrl.target.set(35, 5, 25);
    }
    ctrl.update();
  }

  function render3D(mode) {
    const sc = store.threed.scene;
    if (!sc) return;

    const isDark = document.documentElement.dataset.theme === "dark" || matchMedia("(prefers-color-scheme: dark)").matches;
    sc.background = new THREE.Color(isDark ? 0x0f172a : 0xf1f5f9);

    // Clean up previous meshes (keep lights at index 0 and 1)
    while (sc.children.length > 2) {
      const obj = sc.children[sc.children.length - 1];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
        else obj.material.dispose();
      }
      sc.remove(obj);
    }
    store.threed.clickableNodes = [];

    const isCampus = mode === "3c";
    const levels = isCampus ? ["c"] : ["f0", "f1"];
    const S = isCampus ? 1 / 20 : 1 / 25;
    const baseElevation = { c: 0, f0: 0, f1: store.threed.explodeDist };

    // 1. Ground Plane
    const groundGeo = new THREE.PlaneGeometry(240, 240);
    const groundMat = new THREE.MeshLambertMaterial({
      color: isDark ? 0x1e293b : 0xe2e8f0,
      depthWrite: false
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.15;
    sc.add(ground);

    const colors = {
      bld: 0x93c5fd,
      room: 0xbfdbfe,
      lab: 0x6ee7b7,
      stair: 0xf59e0b,
      bridge: 0x94a3b8,
      field: 0x4ade80,
      park: 0xcbd5e1,
      floor: 0xe2e8f0,
      road: 0xe2e8f0
    };

    // 2. Extruded Rooms & Atrium architecture modeled from photos
    store.graph.rooms
      .filter((r) => levels.includes(r.level))
      .forEach((r) => {
        const b = baseElevation[r.level] || 0;
        let h = 0.4;
        let matColor = colors[r.kind] || 0xcccccc;
        let isTransparent = false;
        let opacityVal = 1.0;

        if (isCampus) {
          if (r.kind === "bld") {
            h = r.label === "VIT" ? 16 : r.label === "M block" ? 13 : r.label === "VP" ? 11 : 8;
            matColor = 0x60a5fa;
          } else if (r.kind === "field") {
            h = 0.1;
            matColor = 0x22c55e;
          } else if (r.kind === "park") {
            h = 0.15;
            matColor = 0x94a3b8;
          }
        } else {
          // Interior Mode: Cantilevered colored volumes modeled from photos
          if (r.label.includes("A1") || r.label.includes("Seminar")) {
            matColor = 0xf59e0b; // Yellow volume
            h = 5.0;
          } else if (r.label.includes("B1") || r.label.includes("Bio")) {
            matColor = 0xf97316; // Orange volume
            h = 5.0;
          } else if (r.kind === "lab") {
            matColor = 0x0ea5e9; // Blue glass box
            isTransparent = true;
            opacityVal = 0.65;
            h = 4.5;
          } else if (r.kind === "bridge") {
            matColor = 0x64748b; // Steel bridge
            h = 0.6;
          } else if (r.kind === "stair") {
            matColor = 0xd97706; // Timber stair
            h = 2.0;
          } else {
            h = 4.5;
            isTransparent = true;
            opacityVal = 0.45;
          }
        }

        const geo = new THREE.BoxGeometry(r.width * S, h, r.height * S);
        const mat = new THREE.MeshLambertMaterial({
          color: matColor,
          transparent: isTransparent,
          opacity: opacityVal,
          depthWrite: !isTransparent
        });

        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set((r.x + r.width / 2) * S, b + h / 2, (r.y + r.height / 2) * S);
        sc.add(mesh);
      });

    // 3. Roof Truss Lines hint over the Atrium in interior mode
    if (!isCampus) {
      const trussGeo = new THREE.BufferGeometry();
      const trussPts = [];
      const f1Y = baseElevation.f1 + 7.0;
      for (let x = 15; x <= 55; x += 8) {
        trussPts.push(new THREE.Vector3(x, f1Y, 10));
        trussPts.push(new THREE.Vector3(x, f1Y, 35));
      }
      for (let z = 10; z <= 35; z += 6) {
        trussPts.push(new THREE.Vector3(15, f1Y, z));
        trussPts.push(new THREE.Vector3(55, f1Y, z));
      }
      trussGeo.setFromPoints(trussPts);
      const trussMat = new THREE.LineBasicMaterial({ color: isDark ? 0x475569 : 0x94a3b8, transparent: true, opacity: 0.5 });
      const trussMesh = new THREE.LineSegments(trussGeo, trussMat);
      sc.add(trussMesh);
    }

    // 4. Nodes and Billboard Labels
    const pos = (n) => new THREE.Vector3(n.x * S, (baseElevation[n.level] || 0) + (isCampus ? 1.0 : 0.8), n.y * S);

    store.graph.nodes
      .filter((n) => levels.includes(n.level) && n.type !== "j")
      .forEach((n) => {
        let col = 0xffffff;
        if (n.id === store.fromId) col = 0x059669;
        else if (n.id === store.toId) col = 0xdc2626;
        else if (n.type === "e") col = 0x10b981;
        else if (n.type === "s") col = 0xf59e0b;
        else if (n.type === "l") col = 0x8b5cf6;

        const isTerminal = (n.id === store.fromId || n.id === store.toId);
        const sphere = new THREE.Mesh(
          new THREE.SphereGeometry(isTerminal ? 1.0 : 0.55, 14, 12),
          new THREE.MeshLambertMaterial({ color: col })
        );
        sphere.position.copy(pos(n));
        sphere.userData = { nodeId: n.id };
        sc.add(sphere);
        store.threed.clickableNodes.push(sphere);

        // Billboard Labels for terminal or landmark nodes
        if (isTerminal || n.type === "e" || n.landmark) {
          const lblText = isTerminal ? (n.id === store.fromId ? "🟢 START" : "🏁 END") : n.label;
          const sprite = makeTextSprite(lblText, isTerminal ? (n.id === store.fromId ? "rgba(5, 150, 105, 0.9)" : "rgba(220, 38, 38, 0.9)") : "rgba(15, 23, 42, 0.75)");
          if (sprite) {
            sprite.position.copy(pos(n)).add(new THREE.Vector3(0, 2.2, 0));
            sc.add(sprite);
          }
        }
      });

    // 5. 3D Route Ribbon & Moving Marker
    if (store.routeData && store.routeData.primary && store.routeData.primary.path) {
      const pts = [];
      store.routeData.primary.path.forEach((id) => {
        const n = store.nodesMap[id];
        if (n && levels.includes(n.level)) pts.push(pos(n));
      });

      if (pts.length >= 2) {
        const curve = new THREE.CatmullRomCurve3(pts);
        store.threed.walkerCurve = curve;
        const tube = new THREE.Mesh(
          new THREE.TubeGeometry(curve, pts.length * 8, 0.45, 8, false),
          new THREE.MeshLambertMaterial({ color: 0xea580c })
        );
        sc.add(tube);

        // Animated walker marker
        const walker = new THREE.Mesh(
          new THREE.SphereGeometry(0.85, 16, 14),
          new THREE.MeshBasicMaterial({ color: 0xfacc15 })
        );
        sc.add(walker);
        store.threed.walkerMesh = walker;

        const box = new THREE.Box3().setFromPoints(pts);
        const center = box.getCenter(new THREE.Vector3());
        store.threed.routeCenter = center;
        store.threed.controls.target.copy(center);
      }
    }

    cancelAnimationFrame(store.threed.raf);
    function animate() {
      store.threed.controls.update();

      if (store.threed.walkerMesh && store.threed.walkerCurve) {
        store.threed.walkerProgress = (store.threed.walkerProgress + 0.003) % 1.0;
        const p = store.threed.walkerCurve.getPointAt(store.threed.walkerProgress);
        store.threed.walkerMesh.position.copy(p);
      }

      store.threed.renderer.render(store.threed.scene, store.threed.camera);
      store.threed.raf = requestAnimationFrame(animate);
    }
    animate();
  }

  // --- DEV GRAPH EDITOR ACTIONS ---
  function exportGraphJson() {
    const blob = new Blob([JSON.stringify(store.graph, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "campus-graph.json";
    a.click();
  }

  async function saveGraphToServer() {
    try {
      const res = await fetch("/api/campus/graph/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(store.graph)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Save failed");
      alert("Campus graph successfully validated by Pydantic and saved to server!");
    } catch (e) {
      alert("Error saving graph: " + e.message);
    }
  }

  function addEditorNode() {
    const id = prompt("Enter unique Node ID (e.g. N_NEW):");
    if (!id || store.nodesMap[id]) {
      alert("Node ID must be unique and non-empty.");
      return;
    }
    const label = prompt("Enter Node Display Label:", id) || id;
    const level = store.viewMode === "editor" ? "c" : store.viewMode;
    const newNode = {
      id,
      label,
      level,
      x: 800,
      y: 400,
      type: "p"
    };
    store.graph.nodes.push(newNode);
    store.nodesMap[id] = newNode;
    render2D();
    alert(`Created node '${id}'. Drag it in editor mode to place it.`);
  }

  // Expose to window
  window.CampusNavigator = {
    store,
    calculateRoute: calculateCampusRoute,
    clearSelection,
    clearEndpoint,
    setEndpoint,
    focusLeg,
    fitToBounds,
    setCameraPreset,
    exportGraphJson,
    saveGraphToServer,
    addEditorNode,
    signCurrentRouteQDS
  };
})();
