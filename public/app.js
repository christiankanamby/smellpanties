document.getElementById("year").textContent = new Date().getFullYear();

fetch("/api/status")
  .then(r => r.json())
  .then(data => {
    document.querySelector(".server-line").classList.add("online");
    document.getElementById("serverText").textContent = data.site_status || "Online";
  })
  .catch(() => {
    document.getElementById("serverText").textContent = "Frontend online";
  });
