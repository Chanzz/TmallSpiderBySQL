import requests
import configparser
import logging, os, time, random, pymysql

shop_name = '左令内衣馆'
PHOTO_DIR = "resources/" + shop_name + "/"
logging.basicConfig(
    filename=os.path.join(os.getcwd(), 'download_img.log'),
    format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',  # 定义输出log的格式
    datefmt='%Y-%m-%d %A %H:%M:%S',  # 时间
    level=logging.INFO,
    filemode='a')


def get_photo(photo_url, name, num):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36'}
    photo = requests.get(photo_url, headers=headers)
    name = name.replace('/', '')
    with open(PHOTO_DIR + name + str(num) + '.jpg', 'wb')as f:
        f.write(photo.content)
        f.flush()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('./config.ini')
    conn = pymysql.connect(host=config.get('DataBase', 'host'),
                           user=config.get('DataBase', 'user'), password=config.get('DataBase', 'password'),
                           db=config.get('DataBase', 'db'), charset=config.get('DataBase', 'charset'))
    cursor = conn.cursor()
    select_sql = "SELECT goods_name,photos_url,goods_url FROM " + shop_name + " WHERE downloaded=0"
    cursor.execute(select_sql)
    result = cursor.fetchall()
    total = len(result)
    now = 1
    for i in result:
        k = i[0]
        v = i[1]
        m = i[2]
        photo_urls = v.split(',')
        print("进度：{}/{} 当前下载商品名：{}  商品地址：{} 文件数：{}".format(now, total, k, m, len(photo_urls)))
        logging.info("进度：{}/{} 当前下载商品名：{}  商品地址：{} 文件数：{}".format(now, total, k, m, len(photo_urls)))
        for j in range(len(photo_urls)):
            get_photo(photo_urls[j], k, j)
        now += 1
        update_sql = "UPDATE " + shop_name + " SET downloaded=1 WHERE goods_url='" + m + "'"
        cursor.execute(update_sql)
        conn.commit()
        time.sleep(random.randint(1, 3))
    cursor.close()
    conn.close()
