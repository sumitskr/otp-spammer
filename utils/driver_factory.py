import undetected_chromedriver as uc


def get_driver(headless=True):
    options = uc.ChromeOptions()

    if headless:
        options.headless = True
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

    # Recommended anti-detection flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")

    # Launch undetected Chrome
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


# if __name__ == "__main__":
#     driver = get_driver(headless=True)
#     driver.get("https://google.com/")
#     print(driver.title)
#     input("Press Enter to quit...")
#     driver.quit()

