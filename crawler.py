import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import telebot
from dotenv import load_dotenv

#load .env
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
USERNAME = os.getenv("MOODLE_USERNAME")
PASSWORD = os.getenv("MOODLE_PASSWORD")
CODE_EXPERT_USERNAME = os.getenv("CODE_EXPERT_USERNAME")
CODE_EXPERT_PASSWORD = os.getenv("CODE_EXPERT_PASSWORD")

CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
CHROMIUM_PATH = "/usr/bin/chromium-browser"

bot = telebot.TeleBot(BOT_TOKEN)

#analysis

def check_analysis():
    URL = "https://metaphor.ethz.ch/x/2025/fs/401-0212-16L/"
    DATA_FILE = "latest_series.txt"

    def get_latest_series():
        r = requests.get(URL)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        tables = soup.find_all("table")
        table = next((t for t in tables if "Aufgabenblatt" in t.text and "Abgabedatum" in t.text), None)
        if not table:
            return None
        rows = table.find_all("tr")[1:]
        series_list = []
        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 2:
                continue
            try:
                datum = datetime.strptime(tds[1].text.strip(), "%d.%m.%Y")
            except:
                continue
            series_list.append((tds[0].text.strip(), datum))
        return max(series_list, key=lambda x: x[1]) if series_list else None

    def load_last():
        if not os.path.exists(DATA_FILE):
            return None
        return open(DATA_FILE).read().strip()

    def save_last(name):
        with open(DATA_FILE, "w") as f:
            f.write(name)

    latest = get_latest_series()
    if not latest:
        return
    name, date = latest
    if name != load_last():
        msg = f"Neue Übungsserie verfügbar in Analysis I: {name}\nAbgabe: {date.strftime('%d.%m.%Y')}"
        bot.send_message(CHAT_ID, msg)
        save_last(name)
        print("Analysis: Neue Serie erkannt.")
    else:
        print("Analysis: Keine neue Serie.")

# codeexpert

def check_code_expert():
    URL = "https://expert.ethz.ch/enrolled/SS25/ALGOWAHR/exercises"
    LOG = "known_exercises.txt"

    def setup_driver():
        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.binary_location = CHROMIUM_PATH
        return webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)

    def login(driver):
        driver.get("https://expert.ethz.ch/login")
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/login/oauth2')]"))).click()
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(CODE_EXPERT_USERNAME)
        time.sleep(2)
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Weiter') or contains(text(),'Continue')]"))).click()
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "password"))).send_keys(CODE_EXPERT_PASSWORD)
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Login')]"))).click()
        WebDriverWait(driver, 30).until(EC.url_contains("enrolled"))

    def extract(driver):
        driver.get(URL)
        time.sleep(10)
        return driver.execute_script("return Array.from(document.querySelectorAll('a[data-test=\"task-action-link\"]')).map(a => a.innerText.trim());")

    known = set(open(LOG).read().splitlines()) if os.path.exists(LOG) else set()
    driver = setup_driver()
    try:
        login(driver)
        tasks = extract(driver)
        new = set(tasks) - known
        if new:
            msg = "📢 *Neue Aufgaben auf Code Expert:*\n\n" + "\n".join(new)
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            with open(LOG, "a") as f:
                for task in new:
                    f.write(task + "\n")
            print("CodeExpert: Neue Aufgaben erkannt.")
        else:
            print("CodeExpert: Keine neuen Aufgaben.")
    except Exception as e:
        print(f"CodeExpert Fehler: {e}")
    finally:
        driver.quit()

#moodle_dashboard

def check_moodle_timeline():
    LOG = "moodle_tasks.log"
    URL = "https://moodle-app2.let.ethz.ch/my/"

    def login():
        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.binary_location = CHROMIUM_PATH
        driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)
        driver.get("https://moodle-app2.let.ethz.ch/auth/shibboleth/login.php")
        time.sleep(3)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "idp"))).find_element(By.XPATH, "//option[contains(text(),'ETH Zürich')]").click()
        driver.find_element(By.ID, "login").submit()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(5)
        return driver

    prev = set(open(LOG).read().splitlines()) if os.path.exists(LOG) else set()
    driver = login()
    try:
        driver.get(URL)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        section = soup.find("section", class_="block_timeline")
        tasks = section.find_all("h6", class_="event-name") if section else []
        new = []
        for task in tasks:
            a = task.find("a")
            if a:
                entry = f"{a.text.strip()} - {a['href']}"
                if entry not in prev:
                    new.append(entry)
        if new:
            msg = "\n\n".join([f"📌 **Neue Aufgabe:** {e.split(' - ')[0]}\\n🔗 [Moodle-Link]({e.split(' - ')[1]})" for e in new])
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            with open(LOG, "a") as f:
                for e in new:
                    f.write(e + "\n")
            print("Moodle Timeline: Neue Einträge gefunden.")
        else:
            print("Moodle Timeline: Keine neuen Einträge.")
    except Exception as e:
        print(f"Moodle Timeline Fehler: {e}")
    finally:
        driver.quit()

#pp

def check_moodle_pp():
    LOG = "moodle_assignments.log"
    URL = "https://moodle-app2.let.ethz.ch/course/view.php?id=24843"

    def login():
        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.binary_location = CHROMIUM_PATH
        driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)
        driver.get("https://moodle-app2.let.ethz.ch/auth/shibboleth/login.php")
        time.sleep(3)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "idp"))).find_element(By.XPATH, "//option[contains(text(),'ETH Zürich')]").click()
        driver.find_element(By.ID, "login").submit()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(5)
        return driver

    prev = set(open(LOG).read().splitlines()) if os.path.exists(LOG) else set()
    driver = login()
    try:
        driver.get(URL)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        links = soup.find_all("a", class_="aalink stretched-link")
        new = [f"{l.text.strip()} - {l['href']}" for l in links if "assignment" in l.text.lower() and f"{l.text.strip()} - {l['href']}" not in prev]
        if new:
            msg = "\n\n".join([f"📌 **Neue Aufgabe:** {e.split(' - ')[0]}\\n🔗 [Moodle-Link]({e.split(' - ')[1]})" for e in new])
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            with open(LOG, "a") as f:
                for e in new:
                    f.write(e + "\n")
            print("Moodle PP: Neue Assignments gefunden.")
        else:
            print("Moodle PP: Keine neuen Assignments.")
    except Exception as e:
        print(f"Moodle PP Fehler: {e}")
    finally:
        driver.quit()

#run

if __name__ == "__main__":
    check_analysis()
    check_code_expert()
    check_moodle_timeline()
    check_moodle_pp()
