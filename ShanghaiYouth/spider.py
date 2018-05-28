# @author	huizhan

import os
from io import StringIO
from datetime import datetime, timedelta

import requests
from lxml import etree


SITE_URL = 'http://app.why.com.cn/epaper/webpc/qnb/html/%s-%s/%s/'
PAPER_PAGE = 'node_1.html'

PDF_ROOT = './pdf/'
if not os.path.exists(PDF_ROOT):
	os.makedirs(PDF_ROOT)


def get_pages(date):

	url = SITE_URL % date
	url += PAPER_PAGE

	raw = requests.get(url)
	html = raw.content
	html = html.decode("utf-8")
	parser = etree.HTMLParser()
	selector = etree.parse(StringIO(html), parser)

	xpath = '//*[@id="table64"]'
	content_table = selector.xpath(xpath)
	pages = content_table[0].findall('.//a')[1::2]
	pages = [page.attrib['href'] for page in pages]

	return pages


def download_page(date, page_pdf_url):

	site_url = SITE_URL % date 
	pdf_url = site_url + page_pdf_url

	pdf = requests.get(pdf_url)
	pdf_name = 'qn'+pdf_url.split('/')[-1]
	with open(PDF_ROOT + pdf_name, 'wb') as f:
		f.write(pdf.content)


def spider(date):

	year = str(date.year)
	month = str(date.month).zfill(2)
	day = str(date.day).zfill(2)
	date = (year, month, day)

	pages = get_pages(date)

	for page in pages:

		for _ in range(3):

			try:
				download_page(date, page)
				break
			except:
				print(date, page, 'try again')

		# tried 3 times, but still failed
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