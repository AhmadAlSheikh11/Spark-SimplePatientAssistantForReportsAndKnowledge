/* Style/main.js (FULL) */
(function () {
  "use strict";

  const lang = (document.documentElement.getAttribute("lang") || "en").toLowerCase();
  const isAR = lang.startsWith("ar");

  const TXT = {
    en: {
      openSoon: "This tool is coming soon (demo).",
      loading: "Loading...",
      saving: "Saving...",
      saved: "Saved.",
      uploading: "Uploading...",
      failed: "Something went wrong.",
      thinking: "Thinking...",
    },
    ar: {
      openSoon: "هذه الأداة قريبًا (تجريبي).",
      loading: "جاري التحميل...",
      saving: "جاري الحفظ...",
      saved: "تم الحفظ.",
      uploading: "جاري الرفع...",
      failed: "حدث خطأ ما.",
      thinking: "جاري التفكير...",
    }
  };
  const t = isAR ? TXT.ar : TXT.en;

  // ---------------- Smooth scroll ----------------
  document.querySelectorAll("[data-scroll]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sel = btn.getAttribute("data-scroll");
      const target = document.querySelector(sel);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  // ---------------- Helpers ----------------
  const onlyDigits = (s) => (s || "").replace(/\D/g, "");
  const validId = (s) => /^\d{8}$/.test(s);

  function qs(name) {
    return new URLSearchParams(window.location.search).get(name);
  }

  function formatSize(bytes) {
    const units = ["B", "KB", "MB", "GB"];
    let v = bytes || 0, i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
  }

  // ---------------- 3D Tilt Cards ----------------
  (function tiltCards() {
    const cards = document.querySelectorAll("[data-tilt]");
    if (!cards.length) return;

    cards.forEach((card) => {
      const maxTilt = 10;
      const scale = 1.02;

      function reset() {
        card.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg) scale(1)";
      }

      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        const x = e.clientX - r.left;
        const y = e.clientY - r.top;
        const midX = r.width / 2;
        const midY = r.height / 2;

        const rotY = ((x - midX) / midX) * maxTilt;
        const rotX = -((y - midY) / midY) * maxTilt;

        card.style.transform = `perspective(900px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) scale(${scale})`;
      });

      card.addEventListener("mouseleave", reset);
      reset();
    });
  })();

  // ---------------- Home: tool-card click opens directly ----------------
  (function toolOpen() {
    document.querySelectorAll("[data-open]").forEach((card) => {
      card.addEventListener("click", (e) => {
        e.preventDefault();
        const what = card.getAttribute("data-open");

        if (what === "cloud") window.location.href = isAR ? "/record_ar" : "/record";
        if (what === "ai") window.location.href = isAR ? "/med_search_ar" : "/med_search";
        if (what === "pain") window.location.href = isAR ? "/pain_3d_ar" : "/pain_3d";
      });
    });
  })();

  // ---------------- Record Page (MED CLOUD) ----------------
  (function recordPage() {
    const patientIdEl = document.getElementById("patientId");
    const reportFiles = document.getElementById("reportFiles");
    const symptomsEl = document.getElementById("symptoms");
    const previewEl = document.getElementById("preview");
    const filesListEl = document.getElementById("filesList");
    const statusEl = document.getElementById("status");
    const saveBtn = document.getElementById("saveSymptoms");
    const loadBtn = document.getElementById("loadRecord");
    const goAI = document.getElementById("goAI");
    const goAI2 = document.getElementById("goAI2");
    const goCloud = document.getElementById("goCloud"); // exists on AI page

    if (!patientIdEl) return;

    const idFromUrl = onlyDigits(qs("id") || "");
    const patientId = validId(idFromUrl) ? idFromUrl : "00000000";
    patientIdEl.textContent = patientId;

    if (goAI) goAI.href = isAR ? `/med_search_ar?id=${patientId}` : `/med_search?id=${patientId}`;
    if (goAI2) goAI2.href = isAR ? `/med_search_ar?id=${patientId}` : `/med_search?id=${patientId}`;
    if (goCloud) goCloud.href = isAR ? `/record_ar?id=${patientId}` : `/record?id=${patientId}`;

    function setStatus(text) {
      if (!statusEl) return;
      statusEl.textContent = text || "";
    }

    function renderFiles(files) {
      if (filesListEl) filesListEl.innerHTML = "";
      if (previewEl) previewEl.innerHTML = "";

      (files || []).forEach((f) => {
        if (filesListEl) {
          const row = document.createElement("div");
          row.className = "file-item";
          const left = document.createElement("span");
          left.textContent = f.original || f.name || "file";
          const right = document.createElement("span");
          right.textContent = f.size ? formatSize(f.size) : "";
          row.appendChild(left);
          row.appendChild(right);
          filesListEl.appendChild(row);
        }

        const url = f.stored || f.preview || "";
        const type = (f.type || "").toLowerCase();
        const looksImage = type.startsWith("image/") || /\.(png|jpg|jpeg|webp|gif)$/i.test(url);

        if (looksImage && url && previewEl) {
          const wrap = document.createElement("div");
          wrap.className = "thumb";
          const img = document.createElement("img");
          img.src = url;
          img.alt = "uploaded";
          wrap.appendChild(img);
          previewEl.appendChild(wrap);
        }
      });
    }

    async function loadRecord() {
      try {
        setStatus(t.loading);
        const r = await fetch(`/api/record/${patientId}`);
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || t.failed);
        const rec = data.record || {};
        if (symptomsEl) symptomsEl.value = rec.symptoms || "";
        renderFiles(rec.files || []);
        setStatus("");
      } catch (e) {
        setStatus(String(e.message || e));
      }
    }

    async function saveSymptoms() {
      try {
        setStatus(t.saving);
        const r = await fetch(`/api/record/${patientId}/symptoms`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symptoms: (symptomsEl ? symptomsEl.value : "") }),
        });
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || t.failed);
        setStatus(t.saved);
      } catch (e) {
        setStatus(String(e.message || e));
      }
    }

    async function uploadFiles(files) {
      if (!files || !files.length) return;
      try {
        setStatus(t.uploading);
        const fd = new FormData();
        Array.from(files).forEach((f) => fd.append("files", f));
        fd.append("symptoms", (symptomsEl ? symptomsEl.value : ""));

        const r = await fetch(`/api/record/${patientId}/upload`, {
          method: "POST",
          body: fd,
        });
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || t.failed);

        const rec = data.record || {};
        renderFiles(rec.files || []);
        setStatus(t.saved);
      } catch (e) {
        setStatus(String(e.message || e));
      }
    }

    if (saveBtn) saveBtn.addEventListener("click", saveSymptoms);
    if (loadBtn) loadBtn.addEventListener("click", loadRecord);
    if (reportFiles) reportFiles.addEventListener("change", () => uploadFiles(reportFiles.files));

    document.querySelectorAll("[data-action='clear-ui']").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (symptomsEl) symptomsEl.value = "";
        if (previewEl) previewEl.innerHTML = "";
        if (filesListEl) filesListEl.innerHTML = "";
        setStatus("");
      });
    });

    loadRecord();
  })();

  // ---------------- AI Page Chat ----------------
  (function aiChat() {
    const chatLog = document.getElementById("chatLog");
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const symptomsEl = document.getElementById("symptoms");
    const patientIdEl = document.getElementById("patientId");
    const saveBtn = document.getElementById("saveSymptoms");
    const loadBtn = document.getElementById("loadSymptoms");
    const statusEl = document.getElementById("status");

    if (!chatLog || !chatForm || !chatInput || !patientIdEl) return;

    const idFromUrl = onlyDigits(qs("id") || "");
    const patientId = validId(idFromUrl) ? idFromUrl : "00000000";
    patientIdEl.textContent = patientId;

    const goCloud = document.getElementById("goCloud");
    if (goCloud) goCloud.href = isAR ? `/record_ar?id=${patientId}` : `/record?id=${patientId}`;

    function setStatus(text) { if (statusEl) statusEl.textContent = text || ""; }

    function addBubble(text, who) {
      const b = document.createElement("div");
      b.className = `bubble ${who === "user" ? "user" : "bot"}`;
      b.textContent = text;
      chatLog.appendChild(b);
      chatLog.scrollTop = chatLog.scrollHeight;
      return b;
    }

    async function loadSymptoms() {
      try {
        setStatus(t.loading);
        const r = await fetch(`/api/record/${patientId}`);
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || t.failed);
        if (symptomsEl) symptomsEl.value = (data.record?.symptoms || "");
        setStatus("");
      } catch (e) {
        setStatus(String(e.message || e));
      }
    }

    async function saveSymptoms() {
      try {
        setStatus(t.saving);
        const r = await fetch(`/api/record/${patientId}/symptoms`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symptoms: (symptomsEl ? symptomsEl.value : "") }),
        });
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || t.failed);
        setStatus(t.saved);
      } catch (e) {
        setStatus(String(e.message || e));
      }
    }

    async function sendChat(message) {
      addBubble(message, "user");
      const typing = addBubble(t.thinking, "bot");

      try {
        const r = await fetch(`/api/ask/${patientId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            symptoms: (symptomsEl ? symptomsEl.value : "")
          }),
        });
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || t.failed);
        typing.textContent = data.answer || t.failed;
      } catch (e) {
        typing.textContent = String(e.message || e);
      }
    }

    if (saveBtn) saveBtn.addEventListener("click", saveSymptoms);
    if (loadBtn) loadBtn.addEventListener("click", loadSymptoms);

    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = (chatInput.value || "").trim();
      if (!text) return;
      chatInput.value = "";
      sendChat(text);
    });

    loadSymptoms();
    addBubble(isAR ? "مرحباً! اكتب سؤالك عن الأعراض." : "Hi! Ask about symptoms or reports.", "bot");
  })();

})();
