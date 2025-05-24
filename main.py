import asyncio
import logging
import random
import time

import yaml
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("automation_playwright.log"),
        logging.StreamHandler()
    ]
)


def load_config():
    with open('config/sites.yaml', 'r') as f:
        return yaml.safe_load(f)


def get_selector(by, locator):
    by = by.lower()
    if by == 'id':
        return f"#{locator}"
    elif by == 'name':
        return f'[name="{locator}"]'
    elif by == 'css':
        return locator
    elif by == 'xpath':
        return f"xpath={locator}"
    elif by == 'placeholder':
        return f'[placeholder="{locator}"]'
    elif by == 'text':
        return f':has-text("{locator}")'
    else:
        raise ValueError(f"Unsupported selector type: {by}")


async def add_stealth(page):
    try:
        with open("config/stealth.min.js", "r") as f:
            stealth_script = f.read()
        await page.add_init_script(stealth_script)
    except FileNotFoundError:
        logging.warning("stealth.min.js not found. Continuing without stealth script.")

    # Override navigator.webdriver
    await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    """)


async def select_country_code(page, country_code_text):
    # Click the dropdown button to open the country code list
    await page.click('button[aria-haspopup="listbox"]')

    # Wait for the dropdown options to appear by visible text
    await page.wait_for_selector(f'text="{country_code_text}"')

    # Click the option with the exact text (e.g. 'India (+91)')
    await page.click(f'text="{country_code_text}"')

    # Optional: small delay to let UI settle after selection
    await asyncio.sleep(0.5)


async def human_type(page, selector, text):
    for char in text:
        await page.type(selector, char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def run_steps(page, steps, phone_number):
    for i, step in enumerate(steps):
        action = step.get('action')
        logging.info(f"Step {i + 1}: Action '{action}'")

        try:
            if action == 'open_url':
                url = step.get('url')
                logging.info(f"Opening URL: {url}")
                # Wait until network idle to ensure page fully loaded
                await page.goto(url, wait_until='networkidle')
                await page.wait_for_selector("body", timeout=5000)

            elif action == 'select_country_code':
                country_code_text = step.get('country_code_text')
                logging.info(f"Selecting country code: {country_code_text}")
                await select_country_code(page, country_code_text)

            elif action in ['click', 'send_keys']:
                locator = step.get('locator')
                by = step.get('by', 'xpath')
                wait_time = step.get('wait', 2)

                selector = get_selector(by, locator)
                logging.info(f"{action.title()} element by [{by}] with locator [{locator}]")
                await page.locator(selector).wait_for(timeout=wait_time * 2000)

                if action == 'click':
                    await page.click(selector)
                    time.sleep(2)
                elif action == 'send_keys':
                    await human_type(page, selector, phone_number)

            else:
                logging.warning(f"Unknown action: {action}")

        except PlaywrightTimeoutError:
            logging.warning(f"Timeout waiting for element in step {i + 1} [{action}]")
        except Exception as e:
            logging.error(f"Exception during step {i + 1} [{action}]: {e}")


async def run_site(context, site_key, site_data, phone_number):
    logging.info(f"Starting automation for site: {site_key}")
    page = await context.new_page()
    await add_stealth(page)

    steps = site_data.get('steps', [])
    if not steps:
        logging.warning(f"No steps found for site: {site_key}")
        await page.close()
        return

    try:
        await run_steps(page, steps, phone_number)
    except Exception as e:
        logging.error(f"Error running steps for {site_key}: {e}")
    finally:
        await page.close()
        logging.info(f"Finished automation for site: {site_key}")


async def main(run_mode='parallel', phone_number='xxxxxxxxx'):
    config = load_config()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )

        tasks = []
        for site_key, site_data in config.items():
            if run_mode == 'parallel':
                tasks.append(run_site(context, site_key, site_data, phone_number))
            else:
                logging.error(f"Invalid run mode: {run_mode}")
                return

        if run_mode == 'parallel':
            await asyncio.gather(*tasks)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(run_mode='parallel'))  # 'parallel' mode only
