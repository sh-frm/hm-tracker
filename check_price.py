import smtplib
import os
import json
import subprocess
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_SENDER   = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
DISCOUNT_THRESHOLD = 50

PRODUCTS = [
    {
        "name": "4er-Pack Boxershorts",
        "url": "https://www2.hm.com/de_de/productpage.1296600003.html",
        "product_code": "1296600003",
    },
]

SCRIPT = """
import asyncio
from playwright.async_api import async_playwright
import json, re, sys

async def get_price(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
        )
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # دنبال قیمت در صفحه
        content = await page.content()
        
        # روش ۱: JSON-LD
        ld = re.findall(r'<script type="application/ld\\+json">(.*?)</script>', content, re.DOTALL)
        for item in ld:
            try:
                d = json.loads(item)
                offers = d.get("offers", {})
                if isinstance(offers, list): offers = offers[0]
                price = offers.get("price") or offers.get("lowPrice")
                if price:
                    print(json.dumps({"sale": float(price), "original": float(price)}))
                    await browser.close()
                    return
            except: pass
        
        # روش ۲: متن قیمت در صفحه
        try:
            price_el = await page.query_selector('[class*="Price"] strong, [data-testid*="price"], .price')
            if price_el:
                text = await price_el.inner_text()
                nums = re.findall(r'[\\d,\\.]+', text)
                prices = [float(n.replace(',','.')) for n in nums if float(n.replace(',','.')) > 1]
                if len(prices) >= 2:
                    print(json.dumps({"original": max(prices), "sale": min(prices)}))
                elif len(prices) == 1:
                    print(json.dumps({"original": prices[0], "sale": prices[0]}))
                await browser.close()
                return
        except: pass
        
        print(json.dumps({"error": "not found"}))
        await browser.close()

asyncio.run(get_price(sys.argv[1]))
"""

def get_price(product_url):
    try:
        result = subprocess.run(
            [sys.executable, "-c", SCRIPT, product_url],
            capture_output=True, text=True, timeout=60
        )
        print(f"  stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()[:200]}")
        
        for line in result.stdout.strip().split('\n'):
            try:
                data = json.loads(line)
                if "error" not in data:
                    original = data.get("original", 0)
                    sale = data.get("sale", 0)
                    discount = round((1 - sale / original) * 100) if original > sale else 0
                    return {"original_price": original, "sale_price": sale, "discount_percent": discount}
            except: pass
    except Exception as e:
        print(f"  خطا: {e}")
    return None


def send_email(product_name, product_url, original_price, sale_price, discount):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎉 تخفیف {discount}٪ روی {product_name}!"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    html_body = f"""
    <div dir="rtl" style="font-family: Arial; padding: 20px;">
        <h2 style="color: #e53e3e;">🔥 تخفیف بیشتر از {DISCOUNT_THRESHOLD}٪ پیدا شد!</h2>
        <h3>{product_name}</h3>
        <p><b>قیمت اصلی:</b> <s>{original_price:.2f} €</s></p>
        <p><b>قیمت با تخفیف:</b> <span style="color:green">{sale_price:.2f} €</span></p>
        <p><b>تخفیف:</b> <span style="color:red">{discount}٪</span></p>
        <a href="{product_url}" style="background:#e53e3e;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;">مشاهده و خرید</a>
    </div>"""
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
    print(f"✅ ایمیل ارسال شد!")


def main():
    print("🔍 بررسی قیمت‌های H&M...")
    for product in PRODUCTS:
        print(f"\n→ {product['name']}")
        info = get_price(product["url"])
        if not info:
            print("  ❌ نتوانستم قیمت را دریافت کنم")
            continue
        print(f"  قیمت اصلی: {info['original_price']:.2f} €")
        print(f"  قیمت فعلی: {info['sale_price']:.2f} €")
        print(f"  تخفیف: {info['discount_percent']}٪")
        if info["discount_percent"] >= DISCOUNT_THRESHOLD:
            send_email(product["name"], product["url"],
                      info["original_price"], info["sale_price"], info["discount_percent"])
        else:
            print(f"  ⏳ تخفیف کافی نیست")
    print("\n✅ بررسی تمام شد.")

if __name__ == "__main__":
    main()
