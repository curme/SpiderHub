# @author   huizhan

"""
    Used to grab people's bank of china webpages.
"""
import os
import sys
import tqdm
import execjs
import requests
from lxml import etree
from io import StringIO
from bs4 import BeautifulSoup
from datetime import datetime
from multiprocessing import Pool

WORKERS = 20
SAVE_ROOT = './articles/'
SITE_ROOT = 'http://www.pbc.gov.cn'
OPEN_TRANS_LIST_ROOT = 'http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html'


# refer to https://www.xusheng.org/blog/2016/10/19/ru-he-zhua-qu-diao-cha-tong-ji-si-de-shu-ju/
# thanks a lot
def get_cookie_header():

    # get cookie's first part
    url = SITE_ROOT
    rep = requests.get(url, allow_redirects=False)
    cookies = ["%s=%s" % (c.name, c.value) for c in rep.cookies]

    soup = BeautifulSoup(rep.text, 'html.parser')
    js_tpl = """
    function func(){
        var window = {innerWidth: 1280, innerHeight: 800, screenX: 0, screenY: 0, screen: {width: 1280, height: 800}};
        var document = (function(){
            var cookies = [];
            return {
                get cookie() { return cookies; },
                set cookie(c) { cookies.push(c); }
            } 
        })();
        %s
        return document.cookie;
    }
    """

    # get cookie's second part
    js_source = js_tpl % soup.find('script').text
    ctx = execjs.compile(js_source)
    cookies2 = [h.split('; ')[0] for h in ctx.call('func')]

    # combine cookie & get ccpassport
    cookies = cookies + cookies2
    headers = { 'Cookie': '; '.join(cookies) }
    rep2 = requests.get(url, headers=headers, allow_redirects=False)

    # return cookie ccpassport
    ccpassport = rep2.cookies['ccpassport']
    return { 'Cookie': 'ccpassport=' + ccpassport }


def get_cookie():

    # get website cookie
    for _ in range(3):
    
        try:
            cookie = get_cookie_header()
            return cookie
        except:
            print('retry getting cookie.')
            continue

    else:
        print('fail to get cookie.')
        sys.exit()


def parse(raw):

	html = raw.content
	html = html.decode("utf-8")
	parser = etree.HTMLParser()
	selector = etree.parse(StringIO(html), parser)

	return selector


def get_list(cookie):

    url = OPEN_TRANS_LIST_ROOT
    count_xpath = '//*[@id="17081"]/div[2]/div[2]/table/tbody/tr/td[2]'
    lpage_xpath = '//*[@id="17081"]/div[2]/div[2]/table/tbody/tr/td[1]/a[4]/@tagname'

    # get html
    r = requests.get(url, headers=cookie)
    selector = parse(r)

    # get page count
    page_count = selector.xpath(count_xpath)
    page_count_str = "".join(page_count[0].itertext())
    count = int(page_count_str.split('/')[-1])

    # get url root
    url_root = selector.xpath(lpage_xpath)[0]
    url_root = '/'.join(url_root.split('/')[:-1])
    url_temp = SITE_ROOT + url_root + '/index%d.html'

    # generate urls
    list_urls = []
    for page_id in range(1, count+1):
        page_url = url_temp % page_id
        list_urls.append(page_url)

    return list_urls


def worker_article_url(urls, cookie):

    artlist_xpath = '//*[@id="17081"]/div[2]/div[1]/table/tbody/tr[2]/td/table/tbody/tr/td[2]'

    article_urls = []
    for url in tqdm.tqdm(urls):

        for _ in range(3):

            try:

                article_urls_tmp = []
                r = requests.get(url, headers=cookie)
                selector = parse(r)
                articles = selector.xpath(artlist_xpath)

                for article in tqdm.tqdm(articles):
                    art_url = article.xpath('font/a/@href')[0]
                    date = article.find('span').text
                    date = datetime.strptime(date, "%Y-%m-%d")
                    article_urls_tmp.append((date.date(), art_url))

                article_urls += article_urls_tmp
                break

            except:

                print('retry getting %s.' % url)
                continue

        else:

            print('fail to get articles in %s.' % url)

    return article_urls


def get_article_urls(cookie):

    urls = []
    list_urls = get_list(cookie)

    # get all articles' url
    results = []
    pool = Pool()
    for worker_id in range(WORKERS):
        sub_urls = list_urls[worker_id::WORKERS]
        result = pool.apply_async(worker_article_url, \
            args=[sub_urls, cookie])
        results.append(result)
    pool.close()
    pool.join()

    articles = []
    for result in results:
        articles += result.get()

    articles.sort()
    return articles


def worker_article(urls, cookie):

    if not os.path.exists(SAVE_ROOT): os.makedirs(SAVE_ROOT)

    for art in tqdm.tqdm(urls):

        date, url = art
        name = datetime.strftime(date, "%Y-%m-%d") + '.html'
        if name in os.listdir(SAVE_ROOT): continue
        url = SITE_ROOT + url

        for _ in range(3):

            try:

                r = requests.get(url, headers=cookie)
                r.encoding = 'UTF-8'
                with open(SAVE_ROOT+name, 'w+') as f:
                    f.write(r.text)
                break

            except:

                print('retry getting %s.' % url)
                continue

        else:

            print('fail to get %s.' % url)
                


def get_articles(cookie, art_urls):

    # get all articles
    pool = Pool()
    for worker_id in range(WORKERS):
        sub_urls = art_urls[worker_id::WORKERS]
        pool.apply_async(worker_article, args=[sub_urls, cookie])
    pool.close()
    pool.join()



if __name__ == "__main__":


    cookie = get_cookie()

    # get all article urls
    art_urls = get_article_urls(cookie)

    # get all articles
    get_articles(cookie, art_urls)

