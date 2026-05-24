document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) {
    return;
  }
  if (!form.matches("[data-disable-on-submit]")) {
    return;
  }

  const button = form.querySelector('button[type="submit"]');
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }

  button.disabled = true;
  if (!button.dataset.originalLabel) {
    button.dataset.originalLabel = button.textContent || "";
  }
  button.textContent = "Working...";
});

document.addEventListener("htmx:afterRequest", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  const button = form.querySelector('button[type="submit"]');
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }

  button.disabled = false;
  if (button.dataset.originalLabel) {
    button.textContent = button.dataset.originalLabel;
  }
});

document.addEventListener("click", async (event) => {
  const target = event.target instanceof Element ? event.target.closest("[data-copy-button]") : null;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const copyTargetId = target.getAttribute("data-copy-target");
  if (!copyTargetId) {
    return;
  }

  const source = document.getElementById(copyTargetId);
  if (!(source instanceof HTMLElement)) {
    return;
  }

  try {
    if (!target.dataset.originalLabel) {
      target.dataset.originalLabel = target.textContent || "Copy output";
    }
    await navigator.clipboard.writeText(source.textContent || "");
    target.textContent = "Copied";
    window.setTimeout(() => {
      target.textContent = target.dataset.originalLabel || "Copy output";
    }, 1200);
  } catch (_error) {
    target.textContent = "Copy failed";
  }
});

document.addEventListener("click", (event) => {
  const toggle = event.target instanceof Element ? event.target.closest("[data-mobile-nav-toggle]") : null;
  if (!(toggle instanceof HTMLButtonElement)) {
    return;
  }

  const header = toggle.closest("[data-mobile-nav]");
  if (!(header instanceof HTMLElement)) {
    return;
  }

  const panel = header.querySelector("[data-mobile-nav-panel]");
  if (!(panel instanceof HTMLElement)) {
    return;
  }

  panel.classList.toggle("hidden");
});
