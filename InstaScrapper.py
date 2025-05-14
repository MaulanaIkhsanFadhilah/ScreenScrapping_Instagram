import asyncio
from playwright.async_api import async_playwright
import json
import re
import os
from datetime import date

# Credentials for Instagram login
IG_USERNAME = "IG_USERNAME"
IG_PASSWORD = "IG_PASSWORD"

# List of target Instagram usernames to scrape
TARGET_USERNAMES = [
    "bogor_update",
    "bogor24update",
    "depok24jam"
]
MAX_POSTS = 5
OUTPUT_DIR = "json"

async def login_instagram(page):
    print("🔐 Login Instagram...")
    await page.goto("https://www.instagram.com/accounts/login/", timeout=60000)
    await page.wait_for_selector('input[name="username"]', timeout=60000)

    await page.fill('input[name="username"]', IG_USERNAME)
    await page.fill('input[name="password"]', IG_PASSWORD)
    await page.click('button[type="submit"]')

    # Tunggu login berhasil
    await page.wait_for_url("https://www.instagram.com", timeout=60000)
    await page.wait_for_timeout(1000)

async def scrape_account(context, target_username):
    page = await context.new_page()
    print(f"\n🔎 Akses profil @{target_username}...")
    await page.goto(f"https://www.instagram.com/{target_username}/", timeout=60000)
    await page.wait_for_selector('div.xg7h5cd.x1n2onr6', timeout=60000)
    await page.wait_for_timeout(3000)

    # Scroll untuk memuat postingan
    for _ in range(3):
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(2000)

    # Kumpulkan URL postingan
    links = await page.locator('div.xg7h5cd.x1n2onr6 a').all()
    post_urls = []
    for link in links:
        href = await link.get_attribute("href")
        if href:
            post_urls.append(f'https://www.instagram.com/{href}')

    post_urls = list(dict.fromkeys(post_urls))[:MAX_POSTS]
    posts = []

    for url in post_urls:
        await page.goto(url, timeout=60000)
        await page.wait_for_selector('div.xt0psk2', timeout=60000)
        await page.wait_for_timeout(2000)

        # Ambil caption
        caption_el = page.locator('div[role="button"] h1').first
        raw_caption = await caption_el.inner_text() if caption_el else ""
        # Hapus hashtag beserta teksnya
        caption = re.sub(r'[#@]\S+', '', raw_caption)
        # Hapus karakter non-permitted
        caption = re.sub(r'[^\w\s,\.\-()/]', '', caption)
        # Ubah semua whitespace (newline, tab, spasi ganda) jadi single space
        caption = re.sub(r'\s+', ' ', caption).strip()

        # Ambil timestamp
        time_el = page.locator('time').first
        timestamp = await time_el.get_attribute("datetime") if time_el else ""

        posts.append({
            "platform": "instagram",
            "username": target_username,
            "text": caption,
            "timestamp": timestamp,
            "url": url,
        })

        print(f"📝 {caption[:80]}")

    await page.close()
    return posts

async def scrape_instagram():
    # Pastikan direktori output ada
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_posts = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # Login sekali
        page = await context.new_page()
        await login_instagram(page)
        await page.close()

        # Scrape tiap akun
        for username in TARGET_USERNAMES:
            account_posts = await scrape_account(context, username)
            all_posts.extend(account_posts)

        await browser.close()

    # Simpan semua data ke satu file JSON
    output_path = os.path.join(OUTPUT_DIR, f"{date.today()}_all_accounts.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Data {len(all_posts)} post dari semua akun disimpan ke {output_path}.")

if __name__ == "__main__":
    asyncio.run(scrape_instagram())
