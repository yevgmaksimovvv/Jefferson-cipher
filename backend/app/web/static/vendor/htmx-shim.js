(function () {
  function toFormBody(form) {
    const params = new URLSearchParams();
    const data = new FormData(form);
    data.forEach((value, key) => {
      params.append(key, value instanceof File ? value.name : String(value));
    });
    return params.toString();
  }

  async function submitHxForm(form) {
    const url = form.getAttribute("hx-post");
    if (!url) {
      return;
    }

    const headers = {
      "HX-Request": "true",
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    };
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: toFormBody(form),
      credentials: "same-origin",
    });

    const targetSelector = form.getAttribute("hx-target");
    const swap = form.getAttribute("hx-swap") || "innerHTML";
    if (targetSelector) {
      const target = document.querySelector(targetSelector);
      if (target) {
        const html = await response.text();
        if (swap === "outerHTML") {
          target.outerHTML = html;
        } else {
          target.innerHTML = html;
        }
      }
    }

    form.dispatchEvent(new Event("htmx:afterRequest", { bubbles: true }));
  }

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    if (!form.hasAttribute("hx-post")) {
      return;
    }

    event.preventDefault();
    submitHxForm(form).catch(() => {
      form.dispatchEvent(new Event("htmx:afterRequest", { bubbles: true }));
    });
  });

  window.htmx = {
    process() {},
  };
})();
