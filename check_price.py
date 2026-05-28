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
    api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}&country_code=de&render=true&wait=3000"
    r = requests.get(api_url, timeout=60)
    print(f"  ScraperAPI status: {r.status_code}")
    return r.text if r.status_code == 200 else None

def parse_discount(html):
    # دنبال بلوکی که هم % داره هم دو قیمت کنار هم (در ۵۰۰ کاراکتر)
    # مثال: -20% ... 23,99 € ... 29,99 €
    matches = list(re.finditer(r'-(\d{1,2})%', html))
    
    for m in matches:
        start = max(0, m.start() - 100)
        end = min(len(html), m.end() + 500)
        chunk = html[start:end]
        
        discount = int(m.group(1))
        if discount < 5 or discount > 95:
            continue
        
        # پیدا کردن قیمت‌ها در همین بلوک
        prices = re.findall(r'(\d+)[,\.](\d{2})\s*€', chunk)
        price_vals = sorted(set(float(f"{p[0]}.{p[1]}") for p in prices))
        
        print(f"  بلوک با {discount}%: قیمت‌ها = {price_vals}")
        
        if len(price_vals) >= 2:
            original = max(price_vals)
            sale = min(price_vals)
            # بررسی اینکه تخفیف با قیمت‌ها همخوانی داشته باشه
            calc_discount = round((1 - sale/original) * 100)
            if abs(calc_discount - discount) <= 10:  # تولرانس ۱۰٪
                print(f"  ✅ قیمت اصلی: {original}€ | فروش: {sale}€ | تخفیف: {discount}%")
                return {"discount": discount, "sale": sale, "original": original}
        elif len(price_vals) == 1:
            original = price_vals[0]
            sale = round(original * (1 - discount/100), 2)
            print(f"  ✅ قیمت اصلی: {original}€ | فروش محاسبه‌شده: {sale}€ | تخفیف: {discount}%")
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
        if info["discount"] >= DISCOUNT_THRESHOLD:
            print("  🎉 تخفیف کافی! ارسال ایمیل...")
            send_email(product["name"], product["url"], info["original"], info["sale"], info["discount"])
        else:
            print(f"  ⏳ تخفیف کافی نیست ({info['discount']}% < {DISCOUNT_THRESHOLD}%)")
    print("\n✅ بررسی تمام شد.")

if __name__ == "__main__":
    main()
