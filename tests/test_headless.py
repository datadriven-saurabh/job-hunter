"""Opt-in integration test: a real Chromium process, no employer requests."""
import asyncio
import os
import tempfile
from pathlib import Path
import pytest
from playwright.async_api import async_playwright
from backend.agents.apply_agent import fill_and_submit

@pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS')!='1',reason='Set RUN_BROWSER_TESTS=1 to exercise installed Chromium')
def test_real_browser_form_execution():
    async def run():
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'resume.pdf';pdf.write_bytes(b'%PDF-1.4\nfixture')
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(headless=True)
                try:
                    page=await browser.new_page()
                    # Any accidental network request is denied.
                    await page.route('**/*',lambda route:route.abort())
                    await page.set_content('''<form onsubmit="event.preventDefault();document.body.innerHTML='<h1>Application submitted</h1>'">
                    <input name="first_name" required><input name="last_name" required>
                    <input type="email" required><input type="tel" required><input type="file" required>
                    <button>Submit application</button></form>''')
                    result=await fill_and_submit(page,{'first_name':'Test','last_name':'Candidate','email':'test@example.com','phone':'+15550102048'},str(pdf))
                    assert result=='SUCCESS'
                    assert await page.get_by_role('heading',name='Application submitted').is_visible()
                    await page.set_content('<form><input type="email" required><input type="checkbox" required><button>Submit application</button></form>')
                    result=await fill_and_submit(page,{'email':'test@example.com'},str(pdf))
                    assert 'Required answers remain' in result
                    assert not await page.locator('input[type="checkbox"]').is_checked()
                    # Exercise the extension's actual content script without installing into a personal browser.
                    await page.set_content('<input name="first_name"><input name="last_name"><input type="email" value="keep@example.com"><input type="tel">')
                    await page.evaluate("window.chrome={runtime:{onMessage:{addListener:fn=>window.fillListener=fn}}}")
                    await page.add_script_tag(path=str(Path(__file__).resolve().parents[1]/'extension/content.js'))
                    result=await page.evaluate("""() => {let result;window.fillListener({action:'AUTOFILL_FORM',formData:{first_name:'Test',last_name:'Candidate',email:'new@example.com',phone:'+15550102048'}},{},r=>result=r);return result;}""")
                    assert result['fieldsFilled']==3
                    assert await page.locator('input[type="email"]').input_value()=='keep@example.com'
                    assert await page.locator('input[name="first_name"]').input_value()=='Test'

                finally:await browser.close()
    asyncio.run(run())
