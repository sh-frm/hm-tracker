import smtplib
import os
import requests
import re
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
    },
]

HEADERS_LIST = [
    {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1", "Accept-Language": "de-DE,de;q=0.9"},
    {"User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36", "Accept-Language": "de-DE"},
    {"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"},
    {"User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"},
]

def get_discount(url):
    for i, headers in enumerate(HEADERS_LIST):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"  Headers {i+1}: status={r.status_code}, size={len(r.text)}")
            
            if r.status_code != 200:
                continue

            # روش ۱: دنبال بج تخفیف -XX%
            discount_badges = re.findall(r'-(\d+)\s*%', r.text)
            if discount_badges:
                discount = max(int(d) for d in discount_badges)
                print(f"  ✅ تخفیف پیدا شد: {discount}%")
                
                # قیمت‌ها
                prices = re.findall(r'(\d+[,\.]\d{2})\s*[€&euro;]|[€&euro;]\s*(\d+[,\.]\d{2})', r.text)
                price_values = []
                for p in prices:
                    val = p[0] or p[1]
                    price_values.append(float(val.replace(',', '.')))
                
                price_values = sorted(set(price_values))
                print(f"  قیمت‌های پیدا شده: {price_values}")
                
                if len(price_values) >= 2:
                    return {"discount": discount, "sale": min(price_values), "original": max(price_values)}
                elif price_values:
                    original = price_values[0]
                    sale = round(original * (1 - discount/100), 2)
                    return {"discount": discount, "sale": sale, "original": original}
            
            # روش ۲: دو قیمت کنار هم (قیمت خط‌خورده)
            struck = re.findall(r'<s[^>]*>.*?(\d+[,\.]\d{2}).*?</s>', r.text)
            current = re.findall(r'class="[^"]*sale[^"]*"[^>]*>.*?(\d+[,\.]\d{2})', r.text)
            if struck and current:
                original = float(struck[0].replace(',', '.'))
                sale = float(current[0].replace(',', '.'))
                if original > sale:
                    discount = round((1 - sale/original) * 100)
                    print(f"  ✅ تخفیف از قیمت خط‌خورده: {discount}%")
                    return {"discount": discount, "sale": sale, "original": original}
            
            print(f"  ⏳ تخفیفی پیدا نشد")
            return {"discount": 0, "sale": 0, "original": 0}
            
        except Exception as e:
            print(f"  Headers {i+1} error: {e}")
    
    return None

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
        info = get_discount(product["url"])
        if info is None:
            print("  ❌ نتوانستم به سایت وصل شوم")
            continue
        if info["discount"] == 0:
            print(f"  ⏳ تخفیفی وجود ندارد")
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
