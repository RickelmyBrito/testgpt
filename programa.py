import sys

from desktop.app import main


def self_test():
    """Validate the packaged Windows runtime on a local page, never on the portal."""
    import tkinter
    from desktop.engine import bundle
    from playwright.sync_api import sync_playwright
    assert tkinter.Tcl().eval('info patchlevel')
    assert 'LoteAulas' in bundle()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page()
        page.set_content('<p id="ok">Programa funcionando</p>')
        assert page.locator('#ok').inner_text() == 'Programa funcionando'
        browser.close()

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        self_test()
    else:
        main()
