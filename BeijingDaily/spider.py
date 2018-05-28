# @author	huizhan

import os
from io import StringIO
from datetime import datetime, timedelta

import requests
from lxml import etree


SITE_URL = 'http://bjrb.bjd.com.cn/html/%s-%s/%s/'
FIRST_PAGE = 'node_1.htm'

PDF_ROOT = './pdf/'
if not os.path.exists(PDF_ROOT):
	os.makedirs(PDF_ROOT)


def download_page(date, selector):

	xpath = '//*[@id="downpdfLink"]/a/@href'
	pdf_url = selector.xpath(xpath)
	pdf_url = SITE_URL % date + pdf_url[0]

	pdf = requests.get(pdf_url)
	pdf_name = 'bjrb' + ''.join(date) + pdf_url.split('/')[-1]
	with open(PDF_ROOT + pdf_name, 'wb') as f:
		f.write(pdf.content)


def parse(url):

	raw = requests.get(url)
	html = raw.content
	html = html.decode("utf-8")
	parser = etree.HTMLParser()
	selector = etree.parse(StringIO(html), parser)

	return selector


def spider(date):

	year = str(date.year)
	month = str(date.month).zfill(2)
	day = str(date.day).zfill(2)
	date = (year, month, day)

	first_page = SITE_URL % date + FIRST_PAGE
	selector = parse(first_page)
	download_page(date, selector)

	while True:

		xpath = '/html/body/div[1]/div/div[2]/div[9]/a/@href'
		next_page = selector.xpath(xpath)

		if len(next_page) == 0: break
		next_page_url = SITE_URL % date + next_page[0]
		

		for _ in range(3):

			try:
				selector = parse(next_page_url)
				download_page(date, selector)
				break
			except:
				print(date, page, 'try again')

		else:

			error = list(date) + page
			error = ','.join(error) + '\n'
			with open('log.txt', 'a') as f:
				f.write(error)



if __name__ == '__main__':

	d1 = timedelta(days=1)
	start_date = datetime(2017,1,1,0,0,0)
	end_date = datetime.today().date()
	date_offset = start_date

	# for i in range(1):
	while date_offset.date() < end_date:

		for _ in range(3):

			try:

				spider(date_offset)
				break

			except:

				print(date_offset, 'try again')


		# tried 3 times, but still failed
		else:

			year = str(date_offset.date().year)
			month = str(date_offset.date().month).zfill(2)
			day = str(date_offset.date().day).zfill(2)
			date = (year, month, day)
			error = list(date)
			error = ','.join(error) + '\n'
			with open('log.txt', 'a') as f:
				f.write(error)

		date_offset += d1