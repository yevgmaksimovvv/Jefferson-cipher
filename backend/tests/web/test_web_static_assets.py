from __future__ import annotations


def test_web_pages_use_local_css_and_semantic_classes(db_client) -> None:
    home_response = db_client.get("/")

    assert home_response.status_code == 200
    assert "/static/app.css" in home_response.text
    assert 'href="/static/app.css"' in home_response.text
    assert 'src="/static/app.js"' in home_response.text
    assert 'src="/static/vendor/htmx-shim.js"' in home_response.text
    assert 'src="/static/vendor/alpine-shim.js"' in home_response.text
    assert "http://localhost/static" not in home_response.text
    assert "https://localhost/static" not in home_response.text
    assert "/static/img/fafawatafa.png" in home_response.text
    assert "Шифр Джефферсона" in home_response.text
    assert "Начать шифрование" in home_response.text
    assert 'href="/cipher"' in home_response.text
    assert "Мои наборы" in home_response.text
    assert 'href="/disk-sets"' in home_response.text
    assert "Что можно сделать" in home_response.text
    assert "Шифровать текст" in home_response.text
    assert "Работать с наборами" in home_response.text
    assert "Сохранять свои наборы" in home_response.text
    assert "API" not in home_response.text
    assert "JSON" not in home_response.text
    assert "OpenAPI" not in home_response.text
    assert "HTTP-контракт" not in home_response.text
    assert "Как начать" not in home_response.text
    assert "Быстрый сценарий" not in home_response.text
    assert "Локальный учебный сервис" not in home_response.text
    assert "Главная" in home_response.text
    assert "Шифр" in home_response.text
    assert "Наборы" in home_response.text
    assert ">JC<" not in home_response.text
    assert "What ships here" not in home_response.text
    assert "Backend-served web UI" not in home_response.text
    assert "No separate frontend service" not in home_response.text
    assert "web surface that stays inside the backend" not in home_response.text
    assert "tailwind.min.js" not in home_response.text
    assert "cdn.tailwindcss.com" not in home_response.text
    assert "unpkg.com" not in home_response.text
    assert "jsdelivr" not in home_response.text
    assert "cdnjs" not in home_response.text
    assert "app-body" in home_response.text or "app-shell" in home_response.text

    cipher_response = db_client.get("/cipher")
    assert cipher_response.status_code == 200
    assert "cipher-layout" in cipher_response.text

    disk_sets_response = db_client.get("/disk-sets")
    assert disk_sets_response.status_code == 200
    assert "disk-page" in disk_sets_response.text


def test_static_app_css_is_present_and_substantial(db_client) -> None:
    response = db_client.get("/static/app.css")

    assert response.status_code == 200
    css = response.text
    assert "--bg: #f6f8fc" in css
    assert ".auth-card" in css
    assert ".home-hero" in css
    assert ".home-cylinder-image" in css
    assert ".home-feature-card" in css
    assert ".feature-icon" in css
    assert ".nav-logo-icon" in css
    assert "width: min(var(--page-max), calc(100% - 48px));" in css
    assert "display: grid; grid-template-columns: auto 1fr auto;" in css
    assert "justify-self: center;" in css
    assert "justify-self: end;" in css
    assert "max-width: 220px;" in css
    assert ".nav-link-active::before" in css
    assert ".nav-link-active::after" in css
    assert "content: none;" in css
    assert "outline: 2px solid rgba(37, 99, 235, 0.55);" in css
    assert ".cipher-layout" in css
    assert ".cipher-form" in css
    assert ".hidden { display: none !important; }" in css
    assert ".desktop-only { display: flex; }" in css
    assert ".mobile-only { display: none !important; }" in css
    assert ".mobile-nav-panel.hidden { display: none !important; }" in css
    assert ".choice-input" in css
    assert ".form-choice:has(.choice-input:checked)" in css
    assert ".disk-grid" in css
    assert ".result-card" in css
    assert ".result-card-header" in css
    assert ".result-text" in css
    assert ".result-empty" in css
    assert ".result-copy-button" in css
    assert ".disk-order-input" in css
    assert ".disk-generator" in css
    assert ".disk-generator-row" in css
    assert ".disk-generator-error" in css
    assert (
        ".page { width: min(var(--page-max), calc(100% - 48px)); margin: 0 auto; "
        "padding: 44px 0 48px; }" in css
    )
    assert ".disk-set-form-page { padding-top: 24px; }" in css
    assert ".example-box" in css
    assert ".example-summary" in css
    assert ".example-code" in css
    assert "cursor: pointer" in css
    assert ".disk-page { display: grid; gap: 36px; padding-top: 12px; }" in css
    assert (
        ".disk-grid { display: grid; grid-template-columns: repeat(auto-fill, "
        "minmax(340px, 1fr)); gap: 18px; }" in css
    )
    assert (
        ".empty-panel { min-width: 0; display: grid; grid-template-columns: "
        "auto minmax(0, 1fr) auto; align-items: center; gap: 18px; padding: 24px; }"
        in css
    )
    assert "overflow-wrap: anywhere;" in css
    assert (
        ".card-metric { min-width: 0; display: grid; grid-template-columns: "
        "auto minmax(0, 1fr); column-gap: 12px; align-items: center; }" in css
    )
    assert (
        ".card-metric dt { color: var(--text-muted); font-size: 14px; "
        "line-height: 1.35; font-weight: 600; }" in css
    )
    assert (
        ".card-metric dd { min-width: 0; margin: 0; color: var(--text); "
        "font-size: 15px; font-weight: 700; line-height: 1.35; "
        "text-align: left; font-variant-numeric: tabular-nums; }" in css
    )
    assert (
        ".card-metric dd.mono-inline { overflow: hidden; white-space: nowrap; "
        "text-overflow: ellipsis; word-break: normal; overflow-wrap: normal; "
        "line-height: 1.35; }" in css
    )
    assert (
        ".btn-danger { background: #fff5f5; color: #b91c1c; "
        "border-color: #f8caca; }" in css
    )
    assert ".explanation-details" in css
    assert ".explanation-summary" in css
    assert ".explanation-step-card" in css
    assert ".card" in css
    assert ".btn-primary" in css
    assert "object-fit: contain" in css
    assert "@media" in css
    assert "inset 0 -2px 0 var(--primary)" not in css
    assert "color-scheme: dark" not in css
    assert "--bg-0" not in css
    assert "--surface-0" not in css
    assert len(css) > 8000


def test_static_hero_image_is_present(db_client) -> None:
    response = db_client.get("/static/img/fafawatafa.png")

    assert response.status_code == 200


def test_static_app_js_and_vendor_shims_are_present(db_client) -> None:
    app_js_response = db_client.get("/static/app.js")
    assert app_js_response.status_code == 200
    assert len(app_js_response.text) > 1000
    assert "secureRandomInt" in app_js_response.text
    assert "crypto.getRandomValues" in app_js_response.text
    assert "shuffleCharacters" in app_js_response.text
    assert "generateDiskLines" in app_js_response.text
    assert "Math.random" not in app_js_response.text
    assert "details:${persistKey}" in app_js_response.text
    assert "data-persist-details" in app_js_response.text
    assert "data-explanation-open-input" in app_js_response.text
    assert "localStorage" in app_js_response.text
    assert "htmx:beforeRequest" in app_js_response.text
    assert "htmx:afterSwap" in app_js_response.text
    assert "htmx:afterSettle" in app_js_response.text

    htmx_response = db_client.get("/static/vendor/htmx-shim.js")
    assert htmx_response.status_code == 200
    assert len(htmx_response.text) > 100

    alpine_response = db_client.get("/static/vendor/alpine-shim.js")
    assert alpine_response.status_code == 200
    assert "window.Alpine" in alpine_response.text
