import smtplib
import os
import requests
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_SENDER      = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD    = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER    = os.environ.get("EMAIL_RECEIVER")
SCRAPER_API_KEY   = os.environ.get("SCRAPER_API_KEY")
DISCOUNT_THRESHOLD = 50

PRODUCTS = [
    {
        "name": "4er-Pack Boxershorts",
        "url": "https://www2.hm.com/de_de/productpage.1296600003.html",
    },
]

def get_page(url):
    """دریافت صفحه از طریق ScraperAPI"""
    api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}&country_code=de"
    r = requests.get(api_url, timeout=60)
    print(f"  ScraperAPI status: {r.status_code}, size: {len(r.text)}")
    return r.text if r.status_code == 200 else None

def parse_discount(html):
    # روش ۱: بج تخفیف -XX%
    badges = re.findall(r'-\s*(\d+)\s*%', html)
    if badges:
        discount = max(int(d) for d in badges)
        print(f"  بج تخفیف پیدا شد: {discount}%")
        
        # قیمت‌ها
        prices = re.findall(r'(\d+)[,\.](\d{2})\s*€', html)
        price_vals = sorted(set(float(f"{p[0]}.{p[1]}") for p in prices))
        print(f"  قیمت‌های پیدا شده: {price_vals}")
        
        if len(price_vals) >= 2:
            return {"discount": discount, "sale": min(price_vals), "original": max(price_vals)}
        elif price_vals:
            original = price_vals[0]
            sale = round(original * (1 - discount/100), 2)
            return {"discount": discount, "sale": sale, "original": original}

    # روش ۲: JSON-LD
    ld = re.findall(r'"price":\s*"?([\d.]+)"?', html)
    if len(ld) >= 2:
        prices = sorted(set(float(p) for p in ld if float(p) > 1))
        if len(prices) >= 2:
            original, sale = max(prices), min(prices)
            discount = round((1 - sale/original) * 100)
            if discount > 0:
                return {"discount": discount, "sale": sale, "original": original}

    print("  تخفیفی پیدا نشد")
    return {"discount": 0, "sale": 0, "original": 0}

def send_email(product_name, product_url, original, sale, discount):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎉 تخفیف {discount}٪ روی {product_name}!"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    html = f"""
    <div dir="rtl" style="font-family:Arial;padding:20px">
        <h2 style="color:#e53e3e">🔥 تخفیف {discount}٪ پیدا شد!</h2>
        <h3>{product_name}</h3>
        <p><b>قیمت اصلی:</b> <s>{original:.2f} €</s></p>
        <p><b>قیمت با تخفیف:</b> <span style="color:green;font-size:1.3em">{sale:.2f} €</span></p>
        <br>
        <a href="{product_url}" style="background:#e53e3e;color:white;padding:12px 24px;text-decoration:none;border-radius:6px">مشاهده و خرید</a>
    </div>"""
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_SENDER, EMAIL_PASSWORD)
        s.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
    print("✅ ایمیل ارسال شد!")

def main():
    print("🔍 بررسی قیمت‌های H&M...")
    for product in PRODUCTS:
        print(f"\n→ {product['name']}")
        html = get_page(product["url"])
        if not html:
            print("  ❌ نتوانستم صفحه را دریافت کنم")
            continue
        info = parse_discount(html)
        if info["discount"] == 0:
            print("  ⏳ تخفیفی وجود ندارد")
            continue
        print(f"  تخفیف: {info['discount']}% | {info['original']:.2f}€ → {info['sale']:.2f}€")
        if info["discount"] >= DISCOUNT_THRESHOLD:
            print("  🎉 تخفیف کافی! ارسال ایمیل...")
            send_email(product["name"], product["url"], info["original"], info["sale"], info["discount"])
        else:
            print(f"  ⏳ تخفیف کافی نیست (نیاز به {DISCOUNT_THRESHOLD}%+)")
    print("\n✅ بررسی تمام شد.")

if __name__ == "__main__":
    main()
