#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on 2020-11-05 15:38:33

import json
from pyspider.libs.base_handler import *


class Handler(BaseHandler):
    crawl_config = {
        'headers': {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'},
    }

    
    #@every(minutes=2)
    @every(minutes=30 * 24 * 60)
    def on_start(self):
        
        url_start = 'https://teacher.school.com/2'
        self.crawl(url_start, callback=self.city_page)

     
    @config(age=1 * 60)
    def city_page(self, response):
        
        # get city list
        city_panel = response.doc('div[class="mcover"]')
        city_codes = [item.attr.cid for item in city_panel('a[class="cityChange"]').items()]
        city_names = [item.text() for item in city_panel('a[class="cityChange"]').items()]
        city_urls = [item.attr.href for item in city_panel('a[class="cityChange"]').items()]
        cities = zip(city_codes, city_names, city_urls)
        
        # get teachers info school by school
        for city_code, city_name, url in cities: 
            data_to_save = {'city_code':city_code, 'city_name':city_name}
            self.crawl(url, callback=self.school_pages, save=data_to_save)
        

    @config(age=1 * 60)
    def school_pages(self, response):
        url_base = response.url
        
        # get page count
        teacher_list_title = response.doc('div[class="teacher_list_t"]')
        right_corner = teacher_list_title('div[class="dl gender"]')
        pager = list(right_corner('p').items())[0]
        page_count = int(list(pager('span').items())[-1].text())
        
        # get teachers page by page
        for offset in range(page_count):
            url = url_base + "/category?p=" + str(offset + 1)
            self.crawl(url, callback=self.school_page, save=response.save)
           
        
    @config(age=1 * 60)
    def school_page(self, response):
        
        # get teachers list
        teacher_panel = response.doc('div[class="teacher_list_b"]')
        teachers = [item.attr.href for item in teacher_panel('a').items()]
        teachers = list(set(teachers))
        
        # get teacher info one by one
        for url in teachers:
            self.crawl(url, callback=self.teacher_page, save=response.save)

    
    @config(priority=5)
    @config(age=10 * 24 * 60 * 60)
    def teacher_page(self, response):
        url_base = response.url
        
        # city info
        city_code = response.save['city_code']
        city_name = response.save['city_name']

        # school name
        school_panel = response.doc('div[class="top_nav"]')('div[class="col-md-3"]')
        school_name = school_panel('a').attr.title
        
        # teacher id
        url_tokens = url_base.split('/')
        teacher_id = url_tokens[-1].split('.')[0]
                
        # teacher category
        category_panel = response.doc('div[class="nav_menu"]')
        category_lis = [item.text() for item in category_panel('a').items()]
        teacher_category = category_lis[-2]

        # teacher info panels
        teacher_panel = response.doc('div[id="con_active"]')        
        teacher_basic_panel = teacher_panel('div[class="active_box1_r"]')
        teacher_tab_titles = teacher_panel('div[class="active_box2_t"]')
        teacher_tabs = teacher_panel('div[class="active_box2_b"]')
                
        # teacher name
        teacher_name_panel = teacher_basic_panel('div[class*="active_box1_r_t"]')
        teacher_name_container = teacher_name_panel('h3')
        teacher_name = teacher_name_container.text()

        # teacher basic
        teacher_basic = {}
        teacher_basic_items = teacher_basic_panel('p[class!="submint"]').items()
        for item in teacher_basic_items:
            item_title = item('strong').text()
            item_title = ''.join(item_title.split('：'))
            item_content = item.remove('strong').text()
            teacher_basic[item_title] = item_content
            
        # teacher tabs id
        tabs_id = {}
        tab_titles = teacher_tab_titles('a').items()
        for tab_title in tab_titles:
            tab_id = tab_title.attr.href.split("#")[-1]
            title = tab_title.text()
            tabs_id[title] = tab_id
            
        # teacher brief
        tab_title_brief = u'\u6559\u5e08\u7b80\u4ecb'
        teacher_brief = {}
        if tab_title_brief in tabs_id:
            brief_tab = teacher_tabs('div[class*="%s"]' % tabs_id[tab_title_brief])
            brief_items = brief_tab('ul > li').items()
            for item in brief_items:
                item_title = item('h4').text()
                item_content = item('div').text()
                if sum(1 for i in item('div > i').items()) > 0:
                    item_content = [i.text() for i in item('div > i').items()]
                teacher_brief[item_title] = item_content
        
        # teacher classes
        tab_title_class = u'TA\u7684\u8bfe\u7a0b'
        if tab_title_class in tabs_id:
            class_tab = teacher_tabs('div[class*="%s"]' % tabs_id[tab_title_class])
            pager = class_tab('select[id="se_sj"]')
            page_count = sum(1 for _ in pager('option').items())
            data_to_save = {'city_code':city_code, 'city_name':city_name, 'teacher_name':teacher_name}
            
            # get teacher classes page by page
            for offset in range(page_count):
                url = url_base + "?p=" + str(offset + 1)
                self.crawl(url, callback=self.class_page, save=data_to_save)
            
        # assemble teacher info
        result = {
            "type": "teacher",
            "url": response.url,
            "title": response.doc('title').text(),
            "city_code": city_code,
            "city_name": city_name,
            "school": school_name,
            "id": teacher_id,
            "name": teacher_name,
            "category": teacher_category,
            "basic": teacher_basic,
            "brief": teacher_brief,
        }
                
        return result
           
        
    @config(priority=3)
    def class_page(self, response):
        url_base = response.url
        
        # city info
        city_code = response.save['city_code']
        city_name = response.save['city_name']
        teacher_name = response.save['teacher_name']

        # school name
        school_panel = response.doc('div[class="top_nav"]')('div[class="col-md-3"]')
        school_name = school_panel('a').attr.title
        
        # teacher id
        url_tokens = url_base.split('/')
        teacher_id = url_tokens[-1].split('.')[0]
    
        # teacher info panels
        teacher_panel = response.doc('div[id="con_active"]')        
        teacher_tab_titles = teacher_panel('div[class="active_box2_t"]')
        teacher_tabs = teacher_panel('div[class="active_box2_b"]')
            
        # teacher tabs id
        tabs_id = {}
        tab_titles = teacher_tab_titles('a').items()
        for tab_title in tab_titles:
            tab_id = tab_title.attr.href.split("#")[-1]
            title = tab_title.text()
            tabs_id[title] = tab_id
        
        # teacher classes
        tab_title_class = u'TA\u7684\u8bfe\u7a0b'
        classes = []
        if tab_title_class in tabs_id:
            class_tab = teacher_tabs('div[class*="%s"]' % tabs_id[tab_title_class])
            class_lis = class_tab('ul[class="js-kecheng-list"] > li').items()
            
            # get class one by one
            for class_item in class_lis:
                class_content = class_item('dd')
                class_name = class_content('h3 > a').text()
                class_url = class_content('h3 > a').attr('href')
                class_time = class_content('div[class*="pp1"] > p').text()
                class_addr = class_content('div[class*="pp2"] > p').text()
                class_info = {
                    "city_code": city_code,
                    "city_name": city_name,
                    "url": class_url,
                    "name": class_name,
                    "school": school_name,
                    "teacher_id": teacher_id,
                    "teacher_name": teacher_name,
                    "time": class_time,
                    "addr": class_addr,
                }
                
                classes.append(class_info)
    
        # assemble class info
        result = {
            "type": "course",
            "url": url_base,
            "title": response.doc('title').text(),
            "city_code": city_code,
            "city_name": city_name,
            "school": school_name,
            "teacher_id": teacher_id,
            "classes": classes,
        }
                
        return result
    
    