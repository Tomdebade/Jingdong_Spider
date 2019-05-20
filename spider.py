# -*- coding:utf-8 -*-
import time
import pymongo
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from pyquery import PyQuery as pq


browser = webdriver.Chrome()
browser.maximize_window()
wait = WebDriverWait(browser, 10)
url = "https://www.jd.com"
keyword = "美食"

MONGO_URL = 'localhost'
MONGO_DB = 'jingdong'
MONGO_COLLECTION = 'products'
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

def search():
    try:
        browser.get(url)
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#key"))
        )
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#search > div > div.form > button"))
        )
        input.send_keys(keyword)
        submit.click()
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#J_bottomPage > span.p-skip > em:nth-child(1) > b"))
        )
        return total.text
    except TimeoutException:
        return search()


def next_page(page_number):
    try:
        input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#J_bottomPage > span.p-skip > input")))
        # if input:
        #     print('Input right!')
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#J_bottomPage > span.p-skip > a")))
        # if submit:
        #     print('Submit right!')
        input.clear()
        input.send_keys(page_number)
        submit.click()
        target = browser.find_element_by_id("J_bottomPage")
        browser.execute_script("arguments[0].scrollIntoView();", target)
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "#J_bottomPage > span.p-num > a.curr"),
                                                    str(page_number)))
    except TimeoutException:
        next_page(page_number)
    except StaleElementReferenceException as msg:
        print('查找元素异常%s'%msg)
        print('重新获取元素')
        target = browser.find_element_by_id("J_bottomPage")
        browser.execute_script("arguments[0].scrollIntoView();", target)
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "#J_bottomPage > span.p-num > a.curr"),
                                                    str(page_number)))


def get_products():
    """
    提取商品数据
    :return:
    """
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#J_goodsList')))
    html = browser.page_source
    doc = pq(html)
    items = doc('#J_goodsList .gl-warp .gl-item').items()
    for item in items:
        product = {
            'title': item.find('.p-name').text().replace('\n', ''),
            'price': item.find('.p-price > strong > i').text(),
            'shop': item.find('.curr-shop').text(),
        }
        if item.find('.p-img > a > img').attr('src'):
            product['image'] = item.find('.p-img > a > img').attr('src')
        else:
            product['image'] = item.find('.p-img > a > img').attr('data-lazy-img')
        yield product


def save_to_mongo(result):
    """
    保存至MongoDB
    :param result: 结果
    :return:
    """
    try:
        if collection.insert_one(result):
            print('存储到MongoDB成功')
    except Exception:
        print('存储到MongoDB失败')


def main():
    try:
        total = search()
        total = int(total)
        for page in range(1, total + 1):
            print('正在爬取第' + str(page) + '页')
            for product in get_products():
                print(product)
                save_to_mongo(product)
            next_page(page + 1)
            time.sleep(1)
            # browser.refresh()
    except Exception:
        print('出错啦')
    finally:
        browser.close()


if __name__=="__main__":
    main()

