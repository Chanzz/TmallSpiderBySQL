from selenium import webdriver
from time import sleep
import requests
from bs4 import BeautifulSoup as bs
import os
import json, time, random
import logging
import pymysql
import configparser

logging.basicConfig(
    filename=os.path.join(os.getcwd(), 'SpiderLog.log'),
    format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',  # 定义输出log的格式
    datefmt='%Y-%m-%d %A %H:%M:%S',  # 时间
    level=logging.ERROR,
    filemode='a')

# 根据店铺页面，获取所有宝贝链接
login_url = 'https://login.taobao.com/member/login.jhtml'
shop_url = 'https://annamiyu.taobao.com/search.htm?spm=2013.1.w5001-17456993967.3.45f219b5ZL2APb&search=y&scene=taobao_shop'


# shop_url = 'https://xinke.tmall.com/search.htm?spm=a220o.1000855.w5001-15325831808.4.255d419bboQnDr&scene=taobao_shop'


# 获取当前页面所有商品链接
def get_good_url(html, good_urls):
    bs_html = bs(html, 'html5lib')
    shop_name = bs_html.find('span', attrs={'class': 'line-left J_TShopLeft'}).find('span',
                                                                                    attrs={'class': 'shop-name'}).find(
        'a').get_text().replace(' ', '')[1:-5]
    # 获取宝贝链接
    item3line1_urls = bs_html.find_all('div', attrs={'class': 'item3line1'})
    for item3line1_url in item3line1_urls:
        detail_url = item3line1_url.find_all('a', attrs={'class': 'item-name'})
        for i in detail_url:
            # 商品名称
            goods_name = i.get_text().replace(' ', '')[:]
            # 商品地址
            good_url = i.attrs['href']
            good_urls[goods_name] = good_url
    return shop_name


def login():
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-automation'])  # 此步骤很重要，设置为开发者模式，防止被各大网站识别出来使用了Selenium
    browser = webdriver.Chrome(options=options)
    browser.get(login_url)
    # 扫码登录时间
    sleep(15)
    return browser


def get_all_page(conn):
    global shop_name
    cursor = conn.cursor()
    goods_urls = {}
    browser = login()
    try:
        for i in range(1, 15):
            print('当前爬取商铺页数：' + str(i))
            current_page_url = shop_url + '&pageNo=' + str(i)
            browser.get(current_page_url)
            list_html = browser.page_source
            shop_name = get_good_url(list_html, goods_urls)
            sleep(10)
    except Exception:
        pass
    # 写入数据库
    create_table_sql = "CREATE TABLE IF NOT EXISTS " + shop_name + "  (id int(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,goods_name varchar(50) CHARACTER SET utf8mb4 NULL,goods_url varchar(255) NULL,data_day date NULL,flag int(2) NULL,photos_url text NULL,comments_url text NULL,downloaded int(2) NULL,UNIQUE INDEX goods_url(goods_url) USING BTREE,INDEX data_day(data_day) USING BTREE)"
    cursor.execute(create_table_sql)
    for k, v in goods_urls.items():
        sql = "SELECT * FROM " + shop_name + " where goods_url='" + v + "'"
        a = cursor.execute(sql)
        if not a:
            insert_sql = "INSERT INTO " + shop_name + "(goods_name,goods_url,data_day,flag)VALUES ('" + k + "','" + v + "','" + time.strftime(
                "%Y-%m-%d", time.localtime()) + "','0')"
            cursor.execute(insert_sql)
            print(v + '  插入成功')
        else:
            print(v + '  已存在')
    conn.commit()
    print("写入数据库成功")
    return browser


def get_photo_url(browser, conn):
    cursor = conn.cursor()
    correct_data(conn)
    select_sql = "SELECT goods_name,goods_url FROM " + shop_name + " WHERE flag=0"
    cursor.execute(select_sql)
    result = cursor.fetchall()
    length = len(result)
    now = 1
    for i in result:
        k = i[0]
        v = i[1]
        print("进度：{}/{}  当前爬取商品名：{}   商品链接：{}".format(now, length, k, v))
        logging.info("进度：{}/{}  当前爬取商品名：{}   商品链接：{}".format(now, length, k, v))
        now += 1
        try:
            browser.get('https:' + v)
        except Exception as e:
            print('错误原因' + str(e))
            logging.error('错误原因' + str(e))
            logging.error('错误位置' + v)
        sleep(random.randint(9, 20))
        browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")
        sleep(random.randint(9, 15))
        html = browser.page_source
        bs_html = bs(html, 'html5lib')
        # 获取图片链接
        photo_urls = bs_html.find('div', attrs={'id': 'J_DivItemDesc', 'class': 'content'}).find_all('img')
        photo = ""
        for i in photo_urls:
            photo_url = i.attrs['src']
            try:
                photo += i.attrs['data-ks-lazyload']
            except:
                photo += photo_url
                pass
            photo += ","
        update_photo_sql = "UPDATE " + shop_name + " SET photos_url='" + photo[
                                                                         :-1] + "' where goods_url='" + v + "'"
        cursor.execute(update_photo_sql)
        conn.commit()
        element = browser.find_element_by_xpath('//*[@id="J_TabBar"]/li[2]/a[@shortcut-label="查看累计评论"]')
        browser.execute_script("arguments[0].click();", element)
        sleep(random.randint(9, 15))
        browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")
        urls = ""
        while True:
            comment_html = bs(browser.page_source, 'html5lib')
            try:
                slider_iframe = comment_html.find('iframe', attrs={'id': 'sufei-dialog-content'})
                if slider_iframe:
                    logging.error("滑块验证------")
                    input("滑块验证============")
                    comment_html = bs(browser.page_source, 'html5lib')
            except:
                pass
            comment_urls = comment_html.find_all('div', attrs={'class': 'tb-rev-item'})
            for comment_url in comment_urls:
                comments = comment_url.find_all('img')
                for comment in comments:
                    a = comment.attrs['src'].split('_')
                    try:
                        urls += 'https:' + a[0] + '_' + a[1]
                    except:
                        pass
                    urls += ","
            sleep(random.randint(10, 20))
            try:
                next_page = browser.find_element_by_class_name('pg-next')
            except Exception:
                print('没有下一页，退出循环')
                break
            try:
                end_page = browser.find_element_by_css_selector('.pg-next.pg-disabled')
                if end_page:
                    print('最后一页，退出循环')
                    break
            except:
                pass
            browser.execute_script("arguments[0].click();", next_page)
            print("进入下一页评论")
        update_comment_sql = "UPDATE " + shop_name + " SET flag=1,comments_url='" + urls[
                                                                                    :-1] + "' where goods_url='" + v + "'"
        conn.ping(reconnect=True)
        cursor = conn.cursor()
        cursor.execute(update_comment_sql)
        conn.commit()
        sleep(random.randint(7, 20))
        if now % 10 == 0:
            time.sleep(30)
    browser.close()


def correct_data(conn):
    cursor = conn.cursor()
    update_sql = "UPDATE " + shop_name + " SET flag=0 where photos_url=''"
    cursor.execute(update_sql)
    conn.commit()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('./config.ini')
    conn = pymysql.connect(host=config.get('DataBase', 'host'), user=config.get('DataBase', 'user'),
                           password=config.get('DataBase', 'password'),
                           db=config.get('DataBase', 'db'), charset=config.get('DataBase', 'charset'))
    browser = get_all_page(conn)
    get_photo_url(browser, conn)
    print('===================================')
