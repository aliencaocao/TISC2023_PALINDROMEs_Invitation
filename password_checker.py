import datetime
import logging
import pickle
import time

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('log.txt')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

scheduler = BackgroundScheduler()
app = Flask(__name__)
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)

home = 'https://discord.com/login?redirect_to=%2Fdevelopers%2Fapplications'


class LocalStorage:
    def __init__(self, driver):
        self.driver = driver
        self.recreate_localStorage_script = '''
            const iframe = document.createElement('iframe');
            document.head.append(iframe);
            const pd = Object.getOwnPropertyDescriptor(iframe.contentWindow, 'localStorage');
            iframe.remove();
            Object.defineProperty(window, 'localStorage', pd);
        '''
        self.driver.execute_script(self.recreate_localStorage_script)  # bypass Discord limitation

    def __len__(self):
        self.driver.execute_script(self.recreate_localStorage_script)
        return self.driver.execute_script("return window.localStorage.length;")

    def items(self):
        self.driver.execute_script(self.recreate_localStorage_script)
        return self.driver.execute_script(
            "var ls = window.localStorage, items = {}; "
            "for (var i = 0, k; i < ls.length; ++i) "
            "  items[k = ls.key(i)] = ls.getItem(k); "
            "return items; ")

    def keys(self):
        self.driver.execute_script(self.recreate_localStorage_script)
        return self.driver.execute_script(
            "var ls = window.localStorage, keys = []; "
            "for (var i = 0; i < ls.length; ++i) "
            "  keys[i] = ls.key(i); "
            "return keys; ")

    def get(self, key):
        self.driver.execute_script(self.recreate_localStorage_script)
        return self.driver.execute_script("return window.localStorage.getItem(arguments[0]);", key)

    def set(self, key, value):
        self.driver.execute_script(self.recreate_localStorage_script)
        self.driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)

    def has(self, key):
        return key in self.keys()

    def remove(self, key):
        self.driver.execute_script(self.recreate_localStorage_script)
        self.driver.execute_script("window.localStorage.removeItem(arguments[0]);", key)


def login():
    logging.info('Getting login page')
    driver.get(home)
    logging.info('Setting local storage')
    with open('localstorage.pkl', 'rb') as f:
        data = pickle.load(f)
    localstorage = LocalStorage(driver)
    for k, v in data.items():
        localstorage.set(k, v)
    driver.refresh()

    driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/form/div[2]/div/div[1]/div[2]/button[2]').click()
    logging.info('Waiting for all applications page')
    all_applications_div = WebDriverWait(driver, 30).until(lambda x: driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[1]/div[3]/div[2]/div/div[1]/div[2]/div[2]/div[2]'))
    return all_applications_div


all_applications_div = login()
apps_str = []
apps_link = []
app_ids = []
in_use = {}  # appid, expire time (15min)
for app_div in all_applications_div.find_elements(By.XPATH, '//*[@id="app-mount"]/div/div/div[1]/div[3]/div[2]/div/div[1]/div[2]/div[2]/div[2]/div'):
    apps_str.append(app_div.find_element(By.TAG_NAME, 'abbr').text)
    apps_link.append(app_div.find_element(By.TAG_NAME, 'a').get_property('href') + '/bot')
    app_ids.append(app_div.find_element(By.TAG_NAME, 'a').get_property('href').split('/')[-1])
logging.info(apps_str)
scheduler.start()
print(app_ids)


def expire(appid: str):
    logging.info(f'Expired {appid}')
    del in_use[appid]
    try:
        get_new_token_by_id(appid)  # resets the token
    except Exception as e:
        logging.error(f'Failed to expire {appid}: {e}')


def get_new_token_by_id(appid: str):
    logging.info(f'Getting new token for {appid}')
    driver.get(apps_link[app_ids.index(appid)])
    WebDriverWait(driver, 30).until(lambda x: driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[1]/div[3]/div[2]/div/div[1]/div[2]/form/div[1]/div[1]/div[2]/div/div[2]/div/div[2]/button')).click()  # reset button
    time.sleep(2)
    driver.find_element(By.XPATH, '/html/body/div[4]/div/footer/button[2]').click()  # confirm button
    time.sleep(3)
    token_div = WebDriverWait(driver, 30).until(lambda x: driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[1]/div[3]/div[2]/div/div[1]/div[2]/form/div[1]/div[1]/div[2]/div/div[2]/div'))
    new_token = token_div.text.split('\n')[2]
    assert len(new_token) == 72, 'Token length is not 72: ' + new_token
    logging.info(f'New token for {appid}: {new_token}')
    return new_token


def get_new_token():
    logging.info('Getting new token from pool')
    if len(in_use) == len(app_ids):
        logging.info('No more tokens left')
        return None
    expire_time = datetime.datetime.now() + datetime.timedelta(minutes=15, seconds=30)
    for sessions in app_ids:
        appid = sessions[session]["appid"]

        if app_id not in in_use:
            try:
                new_token = get_new_token_by_id(app_id)
            except Exception as e:
                logging.error(f'Error getting new token for {app_id}: {e}')
                logging.info('Re-logging in')
                login()
                try:  # retry
                    new_token = get_new_token_by_id(app_id)
                except Exception as e:
                    logging.error(f'Error getting new token for {app_id} even after re-logging in: {e}')
                    continue
                else:
                    in_use[app_id] = expire_time
                    scheduler.add_job(expire, 'date', run_date=expire_time, args=[app_id])
                    return new_token
            else:
                in_use[app_id] = expire_time
                scheduler.add_job(expire, 'date', run_date=expire_time, args=[app_id])
                return new_token
    else:
        return None  # exhausted look as all the tokens errored!


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/check', methods=['POST'])
def check():
    if request.form['password'] == ':dIcH:..uU9gp1<@<3Q"DBM5F<)64S<(01tF(Jj%ATV@$Gl':
        token = get_new_token()
        if token:
            return '<a href=https://discord.gg/2cyZ6zpw7J>Welcome!</a>\n' \
                   f'<!-- {token} -->\n' \
                   f'<!-- You have 15 minutes before this token expires! Find a way to use it and be fast! You can always re-enter the password to get a new token, but please be considerate, it is highly limited. -->'
        else:
            return 'You have the correct password but our challenge infrastructure is currently overloaded and is unable to provide you the required information to continue this challenge. Please try again in 15min, if issue persists, please email tisc_contactus@csit.gov.sg.'
    return 'Incorrect password'


app.run('0.0.0.0', port=7000)
