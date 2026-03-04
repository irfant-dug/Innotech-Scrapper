#python 3.9
# pip install selenium python-dotenv bsoup

import os
import re
import time
import traceback
import json

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()
sites_list = os.getenv('MONITORING_SITES').split(",")

#scraping_variable
tank_dict = {}

tank_menu_item_pattern = re.compile("^Tank.*")
temp_pattern = re.compile(".*Tank Temp$")
chwv_pattern = re.compile(".*Tank CHWV$")


def click_id(driver, element_id):
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID,element_id))
    )
    input_element = driver.find_element(By.ID,element_id)
    input_element.click()

def click_classname(driver, element_classname):
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CLASS_NAME,element_classname))
    )
    input_element = driver.find_element(By.CLASS_NAME,element_classname)
    input_element.click()


def textbox_name(driver, element_name, keys):
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.NAME,element_name))
    )
    input_element = driver.find_element(By.NAME,element_name)

    if element_name == "Password":
        input_element.send_keys(keys + Keys.ENTER)
    else:
        input_element.send_keys(keys)

def logout(driver):
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@class='avatar-wrapper el-dropdown-selfdefine']"))
    )
    input_element = driver.find_element(By.XPATH, "//div[@class='avatar-wrapper el-dropdown-selfdefine']")
    input_element.click()

    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH,"//span[normalize-space()='Log Out']"))
    )
    input_element = driver.find_element(By.XPATH,"//span[normalize-space()='Log Out']")
    input_element.click()

    #wait until login page finish loading
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.NAME,"UserName"))
    )


def scrap_tank_page(html):
    soup = BeautifulSoup(html, "html.parser")
    tank_name = []
    temp = []
    chwv = []

    for row in soup.find_all("div", class_="watch-row el-row"):
        
        #get tank and temp value
        if temp_pattern.match(
            " ".join(((row.find("div", class_="watch-descr el-col el-col-8"))
                .get_text()).split())
        ):
            value = row.find("div", class_="watch-descr el-col el-col-8").get_text()
            tank_name.append((value.split())[0])

            value = row.find("div", class_="watch-value el-col el-col-8").get_text()
            temp.append((value.split())[0])

        #get chwv value
        if chwv_pattern.match(
            " ".join(((row.find("div", class_="watch-descr el-col el-col-8"))
                .get_text()).split())
        ):
            value = row.find("div", class_="watch-value el-col el-col-8").get_text()
            chwv.append((value.split())[0])

    for i in tank_name:
        count = 0
        tank_dict[i] = {"temp": temp[count], "chwv": chwv[count]}
        count += 1

def main():
    #location of chromedriver
    service = Service(executable_path=os.getenv('CHROMEDRIVER_LOCATION'))

    options = Options()
    options.binary_location = os.getenv('CHROMEBINARY_LOCATION')`
    options.add_argument('--headless=new')  #comment for display mode
    options.add_argument("--user-data-dir=/tmp/innotech-scraper-user-data")
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    driver.set_window_size(1920, 1080)

    try:
        for index, site in enumerate(sites_list):
            driver.get('https://' + site + '.dug.com')
            print("scrapping " + site)
            #login
            credential = (os.getenv(site + '_CREDENTIALS')).split(",")
            textbox_name(driver, "UserName", credential[0])
            textbox_name(driver, "Password", credential[1])
    
            #get tank name from side menu
            menu = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".el-submenu.is-active.is-opened"))
            )
            menu_items = menu.find_elements(By.XPATH,".//span")
           
            #iterate for all tank to scrap value
            for item in menu_items:
                if tank_menu_item_pattern.match(item.get_attribute('innerHTML')):
                    item.click()
                    #wait until loading finished
                    WebDriverWait(driver, 30).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".el-loading-mask"))
                    )
                    #wait until value load
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".watch-value.el-col.el-col-8"))
                    )
                    html_source = driver.page_source
                    scrap_tank_page(html_source)

            #print(tank_dict)
            logout(driver)

        #save scrap result to json file
        #use epoch time for time passed calculation
        query_dict = {'epoch_time': str(time.time())}         
        query_dict['tank'] = tank_dict
        with open('tank_metric.json', 'w') as tank_metric:
            json.dump(query_dict, tank_metric)

        print("innotechscrapper great success")
        driver.quit()

    except Exception as e:
        print(e)
        traceback.print_exc()
        driver.save_screenshot("screenshot.png")
        logout(driver)
        driver.quit()

if __name__=="__main__":
    main()
