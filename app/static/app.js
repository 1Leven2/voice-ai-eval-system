document.addEventListener("submit", async (event) => {
  if (event.target.id === "import-form") {
    event.preventDefault();
    const result = document.getElementById("import-result");
    const response = await fetch("/api/import", {method: "POST", body: new FormData(event.target)});
    result.textContent = JSON.stringify(await response.json(), null, 2);
  }
  if (event.target.classList.contains("revision-form")) {
    event.preventDefault();
    const form = event.target;
    const payload = Object.fromEntries(new FormData(form).entries());
    for (const field of ["evidence", "suggestions"]) {
      payload[field] = payload[field].split("\n").map((item) => item.trim()).filter(Boolean);
      if (!payload[field].length) payload[field] = "-";
    }
    const response = await fetch(`/api/samples/${form.dataset.sampleId}/revision`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    form.querySelector(".form-result").textContent = response.ok ? "已保存" : "保存失败";
  }
});
