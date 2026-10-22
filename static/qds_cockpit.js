/**
 * =====================================================================
 * QUANTUM CYBER DEFENSE (QDS) COCKPIT - CLIENT ENGINE
 * Smart India Hackathon 2026 (Problem Statement 26141 - Egreen Quanta)
 * Non-AI Physics-Based Threat Detection, Teleportation & Quantum Ledger
 * =====================================================================
 */

(function () {
  const QDS_STATE = {
    status: null,
    latestResult: null,
    chain: [],
    benchmarks: null,
    activeAttack: "none",
    autoSimulate: false
  };

  const $ = (id) => document.getElementById(id);

  async function initQDSCockpit() {
    try {
      await fetchStatus();
      await fetchLedger();
      await fetchBenchmarks();
      // Run initial baseline legitimate simulation to populate dashboard
      await runSimulation("none");
    } catch (err) {
      console.error("[QDS Cockpit Init Error]", err);
    }
  }

  async function fetchStatus() {
    try {
      const res = await fetch("/api/qds/status");
      if (res.ok) {
        QDS_STATE.status = await res.json();
        updateStatusHeader();
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchLedger() {
    try {
      const res = await fetch("/api/qds/ledger");
      if (res.ok) {
        const data = await res.json();
        QDS_STATE.chain = data.chain || [];
        renderLedger(QDS_STATE.chain, data.integrity);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchBenchmarks() {
    try {
      const res = await fetch("/api/qds/benchmarks");
      if (res.ok) {
        QDS_STATE.benchmarks = await res.json();
        renderBenchmarks(QDS_STATE.benchmarks);
      }
    } catch (e) {
      console.error(e);
    }
  }

  function updateStatusHeader() {
    const s = QDS_STATE.status;
    if (!s) return;
    if ($("qdsKeyLenBadge")) $("qdsKeyLenBadge").textContent = `${s.key_length} Qubits`;
    if ($("qdsSaBadge")) $("qdsSaBadge").textContent = `s_a: ${s.s_a_acceptance}`;
    if ($("qdsSvBadge")) $("qdsSvBadge").textContent = `s_v: ${s.s_v_rejection}`;
  }

  async function runSimulation(attackType) {
    QDS_STATE.activeAttack = attackType;
    const msgInput = $("qdsMessageInput");
    const message = msgInput && msgInput.value.trim() ? msgInput.value.trim() : "Authorized Executive Transit Clearance #2026-ALPHA";

    // Update active button state
    document.querySelectorAll(".qds-attack-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.attack === attackType);
    });

    const loader = $("qdsProcessingOverlay");
    if (loader) loader.style.display = "flex";

    try {
      const res = await fetch("/api/qds/simulate-attack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, attack_type: attackType })
      });

      if (!res.ok) throw new Error("Simulation failed");
      const result = await res.json();
      QDS_STATE.latestResult = result;

      renderThreatTelemetry(result);
      // Refresh ledger to show newly minted block
      await fetchLedger();
    } catch (err) {
      console.error("[QDS Simulation Error]", err);
    } finally {
      if (loader) loader.style.display = "none";
    }
  }

  function renderThreatTelemetry(res) {
    const threat = res.threat_detection;
    const verif = res.verification;
    const attack = res.attack_simulation;
    const receipt = res.blockchain_receipt;

    // 1. Verdict Banner
    const banner = $("qdsVerdictBanner");
    const bannerTitle = $("qdsVerdictTitle");
    const bannerDesc = $("qdsVerdictDesc");
    const bannerBadge = $("qdsVerdictBadge");

    if (banner) {
      banner.className = `qds-verdict-banner ${threat.threat_level.toLowerCase()}`;
    }

    if (bannerTitle) {
      if (threat.threat_level === "SECURE") {
        bannerTitle.innerHTML = "✅ Quantum Signature Verified (Authentic)";
      } else if (threat.threat_level === "MEDIUM") {
        bannerTitle.innerHTML = "⚠️ Threat Flagged: Quantum Channel Manipulation / Eavesdropping";
      } else {
        bannerTitle.innerHTML = `🚨 Threat Blocked: ${threat.threat_type.replace(/_/g, " ")}`;
      }
    }

    if (bannerBadge) {
      bannerBadge.textContent = threat.decision;
      bannerBadge.className = `qds-decision-badge ${threat.decision.toLowerCase()}`;
    }

    if (bannerDesc && threat.explanations && threat.explanations.length > 0) {
      bannerDesc.innerHTML = threat.explanations[0];
    }

    // 2. QBER Meters
    const qberBob = verif.bob.qber;
    const qberCharlie = verif.charlie.qber;
    const discrepancy = verif.discrepancy;
    const sa = verif.thresholds.s_a_acceptance;
    const sv = verif.thresholds.s_v_rejection;

    if ($("qdsBobQberVal")) $("qdsBobQberVal").textContent = `${(qberBob * 100).toFixed(1)}%`;
    if ($("qdsBobBar")) {
      $("qdsBobBar").style.width = `${Math.min(100, qberBob * 200)}%`;
      $("qdsBobBar").className = `qds-meter-fill ${qberBob <= sa ? "green" : (qberBob < sv ? "amber" : "red")}`;
    }

    if ($("qdsCharlieQberVal")) $("qdsCharlieQberVal").textContent = `${(qberCharlie * 100).toFixed(1)}%`;
    if ($("qdsCharlieBar")) {
      $("qdsCharlieBar").style.width = `${Math.min(100, qberCharlie * 200)}%`;
      $("qdsCharlieBar").className = `qds-meter-fill ${qberCharlie <= sa ? "green" : (qberCharlie < sv ? "amber" : "red")}`;
    }

    if ($("qdsDiscrepancyVal")) $("qdsDiscrepancyVal").textContent = `${(discrepancy * 100).toFixed(1)}%`;
    if ($("qdsConfidenceVal")) $("qdsConfidenceVal").textContent = `${threat.physics_metrics.statistical_confidence}%`;
    if ($("qdsPForgeVal")) $("qdsPForgeVal").textContent = threat.physics_metrics.theoretical_forgery_probability;

    // 3. Pauli Measurement Sample Table
    const tableBody = $("qdsMeasurementRows");
    if (tableBody && verif.bob.sample_measurements) {
      tableBody.innerHTML = verif.bob.sample_measurements.map((m, idx) => {
        const charlieM = verif.charlie.sample_measurements[idx] || {};
        const matchClass = m.match ? "match" : "mismatch";
        return `
          <tr>
            <td>Q${m.index}</td>
            <td><span class="basis-chip basis-${m.basis}">${m.basis}-Basis</span></td>
            <td><code>|${m.expected}⟩</code></td>
            <td><code>|${m.outcome}⟩</code></td>
            <td><code>|${charlieM.outcome ?? "-"}⟩</code></td>
            <td><span class="qds-status-dot ${matchClass}"></span>${m.match ? "Match" : "Collapsed"}</td>
          </tr>
        `;
      }).join("");
    }

    // 4. Latest Block Toast
    if (receipt && $("qdsLatestBlockHash")) {
      $("qdsLatestBlockHash").textContent = receipt.block_hash.slice(0, 18) + "...";
      $("qdsLatestBlockIdx").textContent = `#${receipt.block_index}`;
    }
  }

  function renderLedger(chain, integrity) {
    const listEl = $("qdsLedgerChainList");
    if (!listEl) return;

    if ($("qdsLedgerIntegrityBadge")) {
      const ok = integrity && integrity.valid;
      $("qdsLedgerIntegrityBadge").innerHTML = ok 
        ? '<span class="status-chip valid">🟢 Chain Cryptographically Verified</span>' 
        : '<span class="status-chip invalid">🔴 Chain Broken</span>';
    }

    listEl.innerHTML = chain.slice().reverse().map((b) => {
      const isGenesis = b.index === 0;
      const tx = b.transactions[0] || {};
      const threatType = b.quantum_metadata?.threat_type || "NONE";
      const isThreat = threatType !== "NONE";

      return `
        <div class="qds-block-card ${isThreat ? 'threat-block' : ''}">
          <div class="block-header">
            <span class="block-idx">Block #${b.index}</span>
            <span class="block-time">${b.iso_time}</span>
            <span class="block-threat-tag ${isThreat ? 'alert' : 'clean'}">
              ${isGenesis ? 'GENESIS' : (isThreat ? threatType.replace(/_/g, ' ') : 'AUTHENTICATED')}
            </span>
          </div>
          <div class="block-hashes">
            <div class="hash-row"><span>Hash:</span> <code>${b.hash.slice(0, 24)}...</code></div>
            <div class="hash-row"><span>Prev:</span> <code>${b.previous_hash.slice(0, 24)}...</code></div>
            <div class="hash-row"><span>Merkle:</span> <code>${b.merkle_root.slice(0, 24)}...</code></div>
          </div>
          <div class="block-payload">
            <strong>Payload:</strong> ${tx.message || "Genesis Teleportation Key Pool"}
          </div>
        </div>
      `;
    }).join("");
  }

  function renderBenchmarks(benchmarks) {
    const container = $("qdsBenchmarkRows");
    if (!container || !benchmarks || !benchmarks.curves) return;

    container.innerHTML = benchmarks.curves.map((c) => {
      return `
        <tr>
          <td><strong>${c.key_length} Qubits</strong></td>
          <td><code>${c.p_forgery}</code></td>
          <td>${c.log10_security} Orders of Mag</td>
          <td>${c.security_bits_equivalent} bits</td>
          <td>${c.teleportation_qubits} Qubits</td>
          <td>${c.verification_latency_ms} ms</td>
        </tr>
      `;
    }).join("");
  }

  // --- Export to Global Window ---
  window.QDSCockpit = {
    init: initQDSCockpit,
    runSimulation: runSimulation,
    distributeKeys: async function () {
      const btn = $("btnDistributeKeys");
      if (btn) btn.disabled = true;
      try {
        await fetch("/api/qds/distribute-keys", { method: "POST" });
        await runSimulation("none");
      } finally {
        if (btn) btn.disabled = false;
      }
    }
  };
})();
