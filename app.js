document.addEventListener("DOMContentLoaded", () => {
  const checkBtn = document.getElementById("checkBtn");
  const clearBtn = document.getElementById("clearBtn");
  const articleText = document.getElementById("articleText");
  const sourceDomain = document.getElementById("sourceDomain");
  const langHint = document.getElementById("langHint");
  const resultSection = document.getElementById("resultSection");
  const resultLabel = document.getElementById("resultLabel");
  const finalScoreText = document.getElementById("finalScoreText");
  const pFakeEl = document.getElementById("pFake");
  const srcScoreEl = document.getElementById("srcScore");
  const evidenceList = document.getElementById("evidenceList");
  const termsList = document.getElementById("termsList");
  const copyBtn = document.getElementById("copyBtn");
  const themeToggle = document.getElementById("themeToggle");

  // Theme Toggle
  themeToggle.addEventListener("change", (e) => {
    document.body.classList.toggle("theme-cyber", e.target.checked);
    document.body.classList.toggle("theme-modern", !e.target.checked);
  });

  clearBtn.addEventListener("click", () => {
    articleText.value = "";
    sourceDomain.value = "";
    resultSection.classList.add("hidden");
  });

  checkBtn.addEventListener("click", async () => {
    const text = articleText.value.trim();
    const source = sourceDomain.value.trim();
    const lang = langHint.value;

    if (!text) {
      alert("الرجاء إدخال نص الخبر أولاً!");
      return;
    }

    // UI Loading State
    checkBtn.disabled = true;
    checkBtn.textContent = "جاري التحقق... (Checking)";
    
    try {
      const res = await fetch("/api/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source, lang })
      });
      
      if (res.status === 202) {
        alert("النموذج لا يزال يتدرب (Training). الرجاء الانتظار قليلاً والمحاولة مرة أخرى.");
        checkBtn.disabled = false;
        checkBtn.textContent = "تحقق (Verify)";
        return;
      }

      if (!res.ok) {
        const err = await res.json();
        alert("خطأ: " + (err.message || "Server Error"));
        return;
      }

      const data = await res.json();
      resultSection.classList.remove("hidden");

      // --- معالجة النتائج ---
      const pFake = data.p_fake || 0;
      
      // تحديد التسمية واللون
      if (data.label === "fake") {
        resultLabel.innerHTML = "⛔ مزيف (FAKE)";
        resultLabel.style.color = "#ef4444"; // أحمر
      } else if (data.label === "suspicious") {
        resultLabel.innerHTML = "⚠️ مشبوه (SUSPICIOUS)";
        resultLabel.style.color = "#f59e0b"; // برتقالي
      } else {
        resultLabel.innerHTML = "✅ حقيقي (REAL)";
        resultLabel.style.color = "#16a34a"; // أخضر
      }

      // عرض نسبة الثقة
      let confidenceDisplay = data.final_score;
      finalScoreText.textContent = Math.round(confidenceDisplay * 100) + "%";
      pFakeEl.textContent = Number(pFake).toFixed(2);
      
      srcScoreEl.textContent = data.source_score ? Number(data.source_score).toFixed(2) : "-";

      // --- عرض الأدلة (Evidence) ---
      evidenceList.innerHTML = "";
      if (data.evidence && data.evidence.length > 0) {
        data.evidence.forEach(e => {
          // e = [title, similarity_score, stance]
          const li = document.createElement("li");
          const simScore = (e[1] * 100).toFixed(1);
          
          li.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                <strong>📰 مصدر موثوق</strong>
                <small style="color:#666">تطابق: ${simScore}%</small>
            </div>
            <a href="#" style="display:block; color:#00d1b2; text-decoration:none;">${escapeHtml(e[0])}</a>
          `;
          evidenceList.appendChild(li);
        });
      } else {
        evidenceList.innerHTML = "<li style='color:#777; font-style:italic;'>لم يتم العثور على مقالات مشابهة في المصادر الموثوقة (تم الاعتماد على تحليل الذكاء الاصطناعي).</li>";
      }

      // --- عرض الكلمات المفتاحية (Terms) ---
      termsList.innerHTML = "";
      if (data.top_terms && data.top_terms.length > 0) {
        data.top_terms.forEach(t => {
          const li = document.createElement("li");
          li.innerHTML = `<span>${t[0]}</span> <small>(${t[1]})</small>`;
          termsList.appendChild(li);
        });
      } else {
        termsList.innerHTML = "<li>—</li>";
      }

      // تمرير الشاشة للنتائج
      resultSection.scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
      console.error(err);
      alert("خطأ في الاتصال: " + err.message);
    } finally {
      checkBtn.disabled = false;
      checkBtn.textContent = "تحقق (Verify)";
    }
  });

  copyBtn.addEventListener("click", () => {
    const txt = `النتيجة: ${resultLabel.innerText}\nنسبة الثقة: ${finalScoreText.innerText}`;
    navigator.clipboard.writeText(txt).then(() => alert("تم نسخ النتيجة!"));
  });

  function escapeHtml(s) {
    if (!s) return "";
    return s.replace(/[&<>"']/g, m =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[m])
    );
  }
});