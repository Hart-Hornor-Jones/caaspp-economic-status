"""
render_check.py -- open index.html in headless Chromium and exercise every control.

Standard library + Playwright (pip install playwright; then `playwright install chromium`, or point
CHROMIUM_EXECUTABLE at an existing Chromium/Chrome binary). Run from anywhere:

    python tests/render_check.py

The page is served over HTTP from the repository root by the standard library server (the page itself
says to serve the folder over HTTP). The run fails, with exit code 1, on any console error, uncaught
page error, failed network request, or HTTP response of 400 or more, and on any control that does not
produce a drawn chart and table.

What is exercised, at least once each
  * every item of the Test, Compare and Measure menus, for every test and level they apply to
  * both items of the "Average across" and "Schools included" menus (LCFF+ view)
  * the school box: adding schools from the datalist, pooling, the per-chip remove buttons, and the
    12-school limit
  * hovering the chart (tooltip and table-row highlight) and leaving it
  * every entry of the Export menu: SVG, PDF (the print pop-up), PNG at 2x and 4x, copy to clipboard,
    CSV; downloads are received and checked for size and, for the CSV, its header line
  * a narrow viewport (phone width), which uses the page's other legend layout, and the resize handler
"""
from __future__ import annotations

import functools
import http.server
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROBLEMS: list[str] = []
EXERCISED: list[str] = []


def problem(msg):
    PROBLEMS.append(msg)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root: Path):
    handler = functools.partial(QuietHandler, directory=str(root))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}/"


def launch(p):
    exe = os.environ.get("CHROMIUM_EXECUTABLE")
    if exe:
        return p.chromium.launch(executable_path=exe)
    try:
        return p.chromium.launch()
    except Exception as e:                      # no downloaded browser: say so clearly
        raise SystemExit("Playwright's Chromium is not installed: run `playwright install chromium` or set "
                         f"CHROMIUM_EXECUTABLE to a Chromium/Chrome binary.\n{str(e).splitlines()[0]}")


def watch(page, label):
    page.on("console", lambda m: problem(f"console {m.type} [{label}]: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: problem(f"page error [{label}]: {e}"))
    page.on("requestfailed", lambda r: problem(f"request failed [{label}]: {r.url} {r.failure}"))
    page.on("response", lambda r: problem(f"HTTP {r.status} [{label}]: {r.url}") if r.status >= 400 else None)


def drawn(page, what):
    """The chart has data marks (or the page's own 'no results' message) and the table has rows."""
    circles = page.locator("#chart circle").count()
    msg = page.locator("#chart text", has_text="No published results").count()
    rows = page.locator("table.nums tbody tr").count()
    title = page.locator("#plotTitle").inner_text().strip()
    if not ((circles > 0 or msg > 0) and rows > 0 and title):
        problem(f"{what}: chart not drawn (circles={circles}, message={msg}, table rows={rows}, title={title!r})")
    note = page.locator("#exportNote").inner_text().strip()
    if note.startswith("Export failed") or note.startswith("Pop-up blocked"):
        problem(f"{what}: {note}")
    EXERCISED.append(what)


def menu_items(page, btn, host):
    page.click(f"#{btn}")
    labels = page.locator(f"#{host} button").all_inner_texts()
    page.keyboard.press("Escape")
    page.click("body", position={"x": 5, "y": 5})           # closes the menu (document click handler)
    return labels


def choose(page, btn, host, index):
    page.click(f"#{btn}")
    item = page.locator(f"#{host} button").nth(index)
    label = item.inner_text()
    item.click()
    return label


def exercise_menus(page):
    tests = menu_items(page, "btnTest", "menuTest")
    if len(tests) != 2:
        problem(f"Test menu has {len(tests)} items, expected 2")
    for ti in range(len(tests)):
        t = choose(page, "btnTest", "menuTest", ti)
        drawn(page, f"test '{t}'")
        levels = menu_items(page, "btnLevel", "menuLevel")
        for li in range(len(levels)):
            lv = choose(page, "btnLevel", "menuLevel", li)
            drawn(page, f"{t} / compare '{lv}'")
            measures = menu_items(page, "btnMeasure", "menuMeasure")
            if len(measures) < 9:
                problem(f"Measure menu for {t}/{lv} has only {len(measures)} items")
            for mi in range(len(measures)):
                m = choose(page, "btnMeasure", "menuMeasure", mi)
                drawn(page, f"{t} / {lv} / measure '{m}'")
            choose(page, "btnMeasure", "menuMeasure", 0)
            if page.locator("#mwWeight").is_visible():
                for wi in range(len(menu_items(page, "btnWeight", "menuWeight"))):
                    w = choose(page, "btnWeight", "menuWeight", wi)
                    drawn(page, f"{t} / {lv} / average across '{w}'")
                    for pi in range(len(menu_items(page, "btnPanel", "menuPanel"))):
                        pn = choose(page, "btnPanel", "menuPanel", pi)
                        drawn(page, f"{t} / {lv} / {w} / schools included '{pn}'")
            elif lv.startswith("High schools"):
                problem("the weighting and panel menus are hidden in the LCFF+ view")
            if page.locator("#mwSchool").is_visible():
                exercise_schools(page)
            elif lv.startswith("Within one"):
                problem("the school box is hidden in the within-one-school view")


def add_school(page, label):
    page.fill("#school", label)
    page.dispatch_event("#school", "change")


def exercise_schools(page):
    names = page.evaluate("window.CAASPP_ECON.schools.map(s=>`${s.n} — ${s.d} (${s.c})`)")
    options = page.locator("#schoollist option").count()
    if options != len(names):
        problem(f"datalist has {options} options for {len(names)} schools")
    chips = lambda: page.locator("#chips .chip").count()
    if chips() != 1:
        problem(f"expected one default school chip, found {chips()}")
    add_school(page, names[1])
    add_school(page, names[2])
    drawn(page, "school box: three schools pooled")
    if chips() != 3:
        problem(f"after adding two schools expected 3 chips, found {chips()}")
    if page.locator("#chips .hint").inner_text().find("3 schools pooled") < 0:
        problem("pooling hint does not report 3 schools")
    add_school(page, names[1])                                  # duplicate: ignored
    if chips() != 3:
        problem("adding a school twice created a second chip")
    add_school(page, "no such school")
    if chips() != 3:
        problem("an unknown school name created a chip")
    page.locator("#chips .chip .x").first.click()
    drawn(page, "school box: remove-chip button")
    if chips() != 2:
        problem(f"after removing one school expected 2 chips, found {chips()}")
    for nm in names[3:15]:                                      # past the limit of 12
        add_school(page, nm)
    drawn(page, "school box: 12-school limit")
    if chips() != 12:
        problem(f"the pool should be capped at 12 schools, found {chips()}")
    while chips() > 1:
        page.locator("#chips .chip .x").first.click()
    drawn(page, "school box: back to one school")
    if page.locator("#chips .chip .x").count() != 0:
        problem("a lone school chip should have no remove button")


def exercise_hover(page):
    box = page.locator("#chart").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
    page.mouse.move(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.5)
    if not page.locator("#tip").is_visible():
        problem("hovering the chart did not show the tooltip")
    if page.locator("table.nums tr.hl").count() != 1:
        problem("hovering the chart did not highlight a table row")
    page.mouse.move(box["x"] + box["width"] + 50, box["y"] + box["height"] + 50)
    page.mouse.move(5, 5)
    if page.locator("#tip").is_visible():
        problem("the tooltip stayed visible after leaving the chart")
    EXERCISED.append("hover and leave")


def exercise_export(page, context, tmp):
    def download(kind, suffix):
        page.click("#exportBtn")
        with page.expect_download(timeout=30000) as dl:
            page.click(f"#exportMenu button[data-x={kind}]")
        d = dl.value
        path = Path(tmp) / d.suggested_filename
        d.save_as(path)
        if not d.suggested_filename.endswith(suffix) or path.stat().st_size == 0:
            problem(f"export {kind}: got {d.suggested_filename!r} of {path.stat().st_size} bytes")
        EXERCISED.append(f"export {kind}")
        return path

    svg = download("svg", ".svg")
    if "<svg" not in svg.read_text(encoding="utf-8"):
        problem("exported SVG is not an SVG document")
    download("png2", "_2x.png")
    download("png4", "_4x.png")
    csv = download("csv", ".csv")
    lines = csv.read_text(encoding="utf-8").splitlines()
    if len(lines) < 5 or not lines[3].startswith("year,group_a,value_a:"):
        problem(f"exported CSV header unexpected: {lines[:4]}")
    page.click("#exportBtn")
    page.click("#exportMenu button[data-x=copy]")
    page.wait_for_function("document.getElementById('exportNote').textContent.indexOf('Rendering')<0", timeout=30000)
    note = page.locator("#exportNote").inner_text()
    if "PNG" not in note:
        problem(f"copy to clipboard: unexpected note {note!r}")
    EXERCISED.append("export copy")
    page.click("#exportBtn")
    with context.expect_page(timeout=30000) as pop:
        page.click("#exportMenu button[data-x=pdf]")
    popup = pop.value
    watch(popup, "pdf pop-up")
    popup.wait_for_load_state()
    if popup.locator("svg").count() != 1:
        problem("the PDF pop-up does not contain the figure")
    popup.close()
    EXERCISED.append("export pdf")
    page.wait_for_timeout(300)
    if page.locator("#exportMenu.open").count():
        problem("export menu stayed open after a choice")


def exercise_narrow(page):
    page.set_viewport_size({"width": 400, "height": 800})
    page.wait_for_timeout(400)                                  # the resize handler re-renders after 120 ms
    if page.locator("#chart rect[width='12']").count() < 2:
        problem("narrow layout did not draw the two-swatch legend")
    drawn(page, "narrow viewport")
    if page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"):
        problem("page scrolls horizontally at 400 px")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(400)
    drawn(page, "wide viewport again")


def main():
    from playwright.sync_api import sync_playwright

    srv, base = serve(REPO)
    try:
        with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
            browser = launch(p)
            context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True,
                                          permissions=["clipboard-read", "clipboard-write"])
            page = context.new_page()
            watch(page, "index.html")
            try:
                page.goto(base + "index.html", wait_until="load")
                page.wait_for_selector("#chart circle", timeout=30000)
                drawn(page, "initial view")
                if not page.locator("#footurl a").count():
                    problem("footer links not written")
                exercise_menus(page)
                choose(page, "btnTest", "menuTest", 0)
                choose(page, "btnLevel", "menuLevel", 0)
                drawn(page, "statewide CAASPP for export")
                exercise_hover(page)
                exercise_export(page, context, tmp)
                exercise_narrow(page)
            except Exception as e:                  # a timeout or a missing control is a failure, not a crash
                problem(f"stopped after {len(EXERCISED)} views/actions: {type(e).__name__}: {str(e).splitlines()[0]}")
            finally:
                context.close()
                browser.close()
    finally:
        srv.shutdown()
    print(f"exercised {len(EXERCISED)} views/actions")
    if PROBLEMS:
        print(f"\n{len(PROBLEMS)} problem(s):")
        for m in PROBLEMS:
            print(" -", m)
        return 1
    print("render check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
