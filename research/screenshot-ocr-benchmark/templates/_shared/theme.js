// Applies ?theme=light|dark, ?hidetext=1 and ?canonical=1 before first paint.
// hidetext is used only by the ground-truth renderer: the text-hidden render
// must be a fresh first paint, because repainting an already-painted page
// re-rasterizes some anti-aliased edges differently (seen in the pilot).
(function () {
  var params = new URLSearchParams(location.search);
  var theme = params.get("theme") === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", theme);
  if (params.get("hidetext") === "1") document.documentElement.setAttribute("data-hidetext", "1");
  if (params.get("canonical") === "1") document.documentElement.setAttribute("data-canonical", "1");
})();
