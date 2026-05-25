document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) {
    return;
  }
  if (!form.matches("[data-disable-on-submit]")) {
    const confirmMessage = form.getAttribute("data-confirm-delete");
    if (confirmMessage && !window.confirm(confirmMessage)) {
      event.preventDefault();
    }
    return;
  }

  const confirmMessage = form.getAttribute("data-confirm-delete");
  if (confirmMessage && !window.confirm(confirmMessage)) {
    event.preventDefault();
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
  button.textContent = "Выполняется...";
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
      target.dataset.originalLabel = target.textContent || "Скопировать";
    }
    await navigator.clipboard.writeText(source.textContent || "");
    target.textContent = "Скопировано";
    window.setTimeout(() => {
      target.textContent = target.dataset.originalLabel || "Скопировать";
    }, 1200);
  } catch (_error) {
    target.textContent = "Не удалось скопировать";
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

function secureRandomInt(maxExclusive) {
  if (!Number.isInteger(maxExclusive) || maxExclusive <= 0) {
    throw new Error("maxExclusive must be positive");
  }

  const maxUint32 = 0xffffffff;
  const limit = maxUint32 - (maxUint32 % maxExclusive);
  const buffer = new Uint32Array(1);

  do {
    window.crypto.getRandomValues(buffer);
  } while (buffer[0] >= limit);

  return buffer[0] % maxExclusive;
}

function shuffleCharacters(value) {
  const chars = Array.from(value);

  for (let index = chars.length - 1; index > 0; index -= 1) {
    const swapIndex = secureRandomInt(index + 1);
    [chars[index], chars[swapIndex]] = [chars[swapIndex], chars[index]];
  }

  return chars.join("");
}

function generateDiskLines(alphabet, count) {
  const lines = [];

  for (let position = 1; position <= count; position += 1) {
    lines.push(`${position}:${shuffleCharacters(alphabet)}`);
  }

  return lines.join("\n");
}

function setDiskGeneratorError(generator, message) {
  const error = generator.querySelector("[data-disk-generator-error]");
  if (!(error instanceof HTMLElement)) {
    return;
  }

  if (!message) {
    error.textContent = "";
    error.hidden = true;
    return;
  }

  error.textContent = message;
  error.hidden = false;
}

document.addEventListener("click", (event) => {
  const button = event.target instanceof Element ? event.target.closest("[data-generate-disks-button]") : null;
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }

  const generator = button.closest("[data-disk-generator]");
  if (!(generator instanceof HTMLElement)) {
    return;
  }

  const form = generator.closest("form");
  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  const alphabetInput = form.querySelector("[data-alphabet-input]");
  const countInput = generator.querySelector("[data-disk-count-input]");
  const disksTextarea = form.querySelector("[data-disks-textarea]");
  if (
    !(alphabetInput instanceof HTMLInputElement) ||
    !(countInput instanceof HTMLInputElement) ||
    !(disksTextarea instanceof HTMLTextAreaElement)
  ) {
    return;
  }

  const alphabet = alphabetInput.value.trim();
  if (!alphabet) {
    setDiskGeneratorError(generator, "Введите алфавит.");
    return;
  }

  const count = Number(countInput.value.trim());
  if (!Number.isInteger(count) || count < 1 || count > 100) {
    setDiskGeneratorError(generator, "Количество дисков должно быть от 1 до 100.");
    return;
  }

  disksTextarea.value = generateDiskLines(alphabet, count);
  setDiskGeneratorError(generator, "");
});

function getPersistKey(details) {
  const persistKey = details.dataset.persistDetails;
  if (!persistKey) {
    return null;
  }

  return `details:${persistKey}`;
}

function readPersistedDetailsState(details) {
  const persistKey = getPersistKey(details);
  if (!persistKey) {
    return null;
  }

  try {
    const state = window.localStorage.getItem(persistKey);
    return state === "open" || state === "closed" ? state : null;
  } catch (_error) {
    return null;
  }
}

function syncExplanationOpenInput(details, root = document) {
  const input = root.querySelector("[data-explanation-open-input]");
  if (!(input instanceof HTMLInputElement)) {
    return;
  }

  input.value = details.open ? "1" : "0";
}

function writePersistedDetailsState(details) {
  const persistKey = getPersistKey(details);
  if (!persistKey) {
    return;
  }

  try {
    window.localStorage.setItem(persistKey, details.open ? "open" : "closed");
  } catch (_error) {
    return;
  }
}

function restorePersistedDetailsState(root = document) {
  const detailsList = root.querySelectorAll("details[data-persist-details]");
  detailsList.forEach((details) => {
    if (!(details instanceof HTMLDetailsElement)) {
      return;
    }

    const persistedState = readPersistedDetailsState(details);
    if (persistedState === null) {
      return;
    }

    details.open = persistedState === "open";
    syncExplanationOpenInput(details, details.closest("form") ?? root);
  });
}

document.addEventListener(
  "toggle",
  (event) => {
    const details = event.target instanceof HTMLDetailsElement ? event.target : null;
    if (!(details instanceof HTMLDetailsElement)) {
      return;
    }

    if (!details.dataset.persistDetails) {
      return;
    }

    syncExplanationOpenInput(details, details.closest("form") ?? document);
    writePersistedDetailsState(details);
  },
  true,
);

document.addEventListener("htmx:beforeRequest", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  const details = form.closest("#cipher-workspace")?.querySelector(
    "details[data-persist-details='cipher-explanation']",
  );
  if (!(details instanceof HTMLDetailsElement)) {
    return;
  }

  syncExplanationOpenInput(details, form);
  writePersistedDetailsState(details);
});

document.addEventListener("htmx:afterSwap", () => {
  restorePersistedDetailsState(document);
});

document.addEventListener("htmx:afterSettle", () => {
  restorePersistedDetailsState(document);
});

document.addEventListener("DOMContentLoaded", () => {
  restorePersistedDetailsState(document);
});

if (document.readyState !== "loading") {
  restorePersistedDetailsState(document);
}
