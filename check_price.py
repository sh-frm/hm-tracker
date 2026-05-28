import requests
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# ═══════════════════════════════════════════
#  تنظیمات - اینجا رو پر کن
# ═══════════════════════════════════════════
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER")    # ایمیل Gmail فرستنده
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")  # App Password گوگل
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")  # ایمیل دریافت‌کننده
DISCOUNT_THRESHOLD = 50                            # درصد تخفیف

PRODUCTS = [
    {
        "name": "4er-Pack Boxershorts",
        "url": "https://www2.hm.com/de_de/productpage.1296600003.html",
        "product_id": "1296600003",
        "target_size": "L",
    },
    # محصول دوم رو اینجا اضافه کن (بعد از پیدا کردن ID اش)
    # {
    #     "name": "5er-Pack Boxershorts",
    #     "url": "https://www2.hm.com/de_de/productpage.XXXXXXXXX.html",
    #     "product_id": "XXXXXXXXX",
    #     "target_size": "L",
    # },
]

# ═══════════════════════════════════════════
#  دریافت اطلاعات قیمت از H&M API
# ═══════════════════════════════════════════
def get_product_info(product_id):
    api_url = f"https://www2.hm.com/de_de/getJsonPageData.json?id={product_id}&category=boxershorts&page=productdetails"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "de-DE,de;q=0.9",
    }

    # روش اول: JSON API
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return parse_api_response(data)
    except Exception:
        pass

    # روش دوم: scrape مستقیم صفحه
    try:
        page_url = f"https://www2.hm.com/de_de/productpage.{product_id}.html"
        resp = requests.get(page_url, headers=headers, timeout=15)
        return parse_html_response(resp.text, product_id)
    except Exception as e:
        print(f"خطا در دریافت اطلاعات محصول {product_id}: {e}")
        return None


def parse_api_response(data):
    try:
        product = data.get("product", {})
        price_info = product.get("price", {})
        original = price_info.get("regularPrice", {}).get("value", 0)
        sale = price_info.get("salePrice", {}).get("value", 0)

        if original and sale:
            discount = round((1 - sale / original) * 100)
            return {
                "original_price": original,
                "sale_price": sale,
                "discount_percent": discount,
                "name": product.get("name", ""),
            }
    except Exception:
        pass
    return None


def parse_html_response(html, product_id):
    """استخراج قیمت از HTML با regex ساده"""
    import re

    # دنبال JSON داخل صفحه می‌گردیم
    pattern = r'"regularPrice":\s*\{[^}]*"value":\s*([\d.]+)'
    sale_pattern = r'"salePrice":\s*\{[^}]*"value":\s*([\d.]+)'

    reg_match = re.search(pattern, html)
    sale_match = re.search(sale_pattern, html)

    if reg_match and sale_match:
        original = float(reg_match.group(1))
        sale = float(sale_match.group(1))
        discount = round((1 - sale / original) * 100)
        return {
            "original_price": original,
            "sale_price": sale,
            "discount_percent": discount,
            "name": f"محصول {product_id}",
        }
    return None


# ═══════════════════════════════════════════
#  ارسال ایمیل
# ═══════════════════════════════════════════
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
        <p><b>قیمت با تخفیف:</b> <span style="color:green; font-size:1.3em;">{sale_price:.2f} €</span></p>
        <p><b>میزان تخفیف:</b> <span style="color:red; font-weight:bold;">{discount}٪</span></p>
        <br>
        <a href="{product_url}" style="background:#e53e3e; color:white; padding:12px 24px; 
           text-decoration:none; border-radius:6px;">مشاهده و خرید</a>
    </div>
    """

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

    print(f"✅ ایمیل ارسال شد! تخفیف {discount}٪ برای {product_name}")


# ═══════════════════════════════════════════
#  اجرای اصلی
# ═══════════════════════════════════════════
def main():
    print("🔍 بررسی قیمت‌های H&M...")

    for product in PRODUCTS:
        print(f"\n→ {product['name']} (ID: {product['product_id']})")
        info = get_product_info(product["product_id"])

        if not info:
            print("  ❌ نتوانستم اطلاعات قیمت را دریافت کنم")
            continue

        print(f"  قیمت اصلی: {info['original_price']:.2f} €")
        print(f"  قیمت فعلی: {info['sale_price']:.2f} €")
        print(f"  تخفیف: {info['discount_percent']}٪")

        if info["discount_percent"] >= DISCOUNT_THRESHOLD:
            print(f"  🎉 تخفیف کافی! در حال ارسال ایمیل...")
            send_email(
                product_name=product["name"],
                product_url=product["url"],
                original_price=info["original_price"],
                sale_price=info["sale_price"],
                discount=info["discount_percent"],
            )
        else:
            print(f"  ⏳ تخفیف کافی نیست (نیاز به {DISCOUNT_THRESHOLD}٪+)")

    print("\n✅ بررسی تمام شد.")


if __name__ == "__main__":
    main()
