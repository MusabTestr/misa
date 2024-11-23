import requests
import re
import telebot
import os
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# توكن البوت
API_TOKEN = "7185882998:AAGlqixECUAK7hBivO6kTC5GD4YgP0rS5go"
bot = telebot.TeleBot(API_TOKEN)

# مواقع موثوقة لسحب البروكسيات حسب النوع
urls = {
    "http": [
        "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    ],
    "https": [
        "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/https.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/https.txt"
    ],
    "socks4": [
        "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks4.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks4.txt",
        "https://www.proxy-list.download/api/v1/get?type=socks4",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt",
        "https://www.proxy-list.download/api/v1/get?type=socks5",
        "https://www.socks-proxy.net/",
    ],
}

# تهيئة المحاولات المتعددة للاتصال
def get_with_retry(url):
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    response = session.get(url, verify=False)
    return response

# جلب البروكسيات من المواقع بشكل متوازي
def fetch_proxies_from_url(url):
    try:
        print(f"جاري جلب البروكسيات من: {url}")
        response = get_with_retry(url)
        if response.status_code == 200:
            if "<html" in response.text.lower():
                return extract_proxies_from_html(response.text)
            else:
                return response.text.splitlines()
        else:
            print(f"فشل الاتصال بالموقع: {url}")
    except Exception as e:
        print(f"حدث خطأ أثناء الاتصال بـ {url}: {e}")
    return []

def fetch_proxies(proxy_type):
    if proxy_type not in urls:
        return []

    proxies = set()  # استخدام set لتجنب تكرار البروكسيات
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_proxies_from_url, url) for url in urls[proxy_type]]
        for future in futures:
            proxies.update(future.result())

    return clean_proxies(list(proxies))

# تنظيف البروكسيات (الصيغة: IP:Port فقط)
def clean_proxies(proxies):
    cleaned_proxies = []
    for proxy in proxies:
        match = re.match(r"(\d+\.\d+\.\d+\.\d+:\d+)", proxy)
        if match:
            cleaned_proxies.append(match.group(1))
    return cleaned_proxies

# استخراج البروكسيات من HTML
def extract_proxies_from_html(html):
    pattern = r"(\d+\.\d+\.\d+\.\d+:\d+)"
    return re.findall(pattern, html)

# حفظ البروكسيات في ملف
def save_proxies(proxies, proxy_type):
    filename = f"{proxy_type}_proxies.txt"
    with open(filename, "w") as file:
        file.write("\n".join(proxies))
    return filename

# حذف الملف بعد إرساله
def delete_file(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print(f"حدث خطأ أثناء حذف الملف: {e}")

# التعامل مع الأمر start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! Choose the type of proxy:\n1. HTTP\n2. HTTPS\n3. SOCKS4\n4. SOCKS5\n5. ALL")

# عرض رسالة متحركة أثناء الانتظار
def show_waiting_message(chat_id):
    waiting_msg = bot.send_message(chat_id, "Please wait… Fetching the proxies 🕒")
    sleep(1)
    bot.edit_message_text("Please wait… Fetching the proxies 🕓", chat_id, waiting_msg.message_id)
    sleep(1)
    bot.edit_message_text("Please wait… Fetching the proxies 🕔", chat_id, waiting_msg.message_id)
    sleep(1)
    bot.edit_message_text("Please wait… Fetching the proxies 🕙", chat_id, waiting_msg.message_id)
    return waiting_msg

# التعامل مع استجابة المستخدم واختيار البروكسيات
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_choice = message.text.strip()
        proxy_type_map = {
            "1": "http",
            "2": "https",
            "3": "socks4",
            "4": "socks5",
            "5": "all",
        }

        proxy_type = proxy_type_map.get(user_choice)
        if proxy_type:
            waiting_msg = show_waiting_message(message.chat.id)

            if proxy_type == "all":
                all_proxies = []
                for key in ["http", "https", "socks4", "socks5"]:
                    all_proxies.extend(fetch_proxies(key))
                proxies = list(set(all_proxies))  # إزالة التكرارات
                filename = save_proxies(proxies, "all")
            else:
                proxies = fetch_proxies(proxy_type)
                filename = save_proxies(proxies, proxy_type)

            if proxies:
                with open(filename, "rb") as file:
                    bot.send_document(message.chat.id, file, caption=f" {proxy_type} ✅")
                delete_file(filename)
            else:
                bot.reply_to(message, "لم يتم جلب أي بروكسيات!")

            bot.delete_message(message.chat.id, waiting_msg.message_id)
        else:
            bot.reply_to(message, "اختيار غير صحيح! يرجى اختيار رقم بين 1 و 5.")
    except Exception as e:
        print(f"حدث خطأ أثناء معالجة الرسالة: {e}")
        bot.reply_to(message, "حدث خطأ غير متوقع. حاول لاحقًا.")

# تشغيل البوت
if __name__ == "__main__":
    bot.polling(non_stop=True, timeout=60)
