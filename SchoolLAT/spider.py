#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on 2020-11-08 10:43:12

import time
import hmac
import json
import math
import random
import hashlib
from urlparse import urlparse
from pyspider.libs.base_handler import *


class Handler(BaseHandler):
    host = 'https://mini.school.com'
    crawl_config = {
        #'itag': 'v223',
        'headers': {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-cn",
            "Connection": "keep-alive",
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/7.0.18(0x17001227) NetType/WIFI Language/zh_CN',
            "Host": urlparse(host).netloc,
        },
    }
    
    common_headers = {
        "scene": "",
        "client_type":"",
        "accessid": "mini",                     
        "version": "3.4.1", 
        "Authorization": "", 
    }
    
    # course request data
    course_data = {
      "astIds": "short",
      "platform": "iOS",
      "mode": 2,
      "limit": 20,
      "subjectIds": 9999,
      "term": 9999,
      "page": 1,
      "levelIds": 9999,
      "isHiddenFull": 0,
      "teaId": 9999,
      "tutorTeaId": 9999,
      "timeType": "",
      "claCourseType": "",
      "venueId": ""
    }
    
    # signature inputs
    digits = "0123456789"
    letters = "abcdefghijklmnopqrstuvwxyz"
    private_key = "miniSCHOOL".encode('utf-8')
    headers_list = [
        "area", "gradeId", "devid", "v", "stu_id", "client_type", "timestamp", 
        "accessid", "nonce", "algorithm", "version", "authorization" 
    ]

    
    #@every(minutes=30 * 24 * 60)
    def on_start(self):
        
        # init headers
        headers_cities = self.init_headers()
        headers_cities['sign'] = self.sign({}, headers_cities)
        headers_cities.update({"Content-Length":0})
        
        # get cities
        url_start = self.host + '/_mock_/user/opencity'
        self.crawl(url_start, callback=self.cities_page, headers=headers_cities)

     
    @config(age=1 * 60)
    def cities_page(self, response):
        
        # get city list
        initials, cities = response.json['data'], []
        for i in initials: cities += initials[i]
            
        # get teacher city by city
        city_grade_url = self.host + "/_mock_/course/gradebycity"
        for city in cities: 
            
            data = {'area_code':str(city['area_code'])}
            data_to_convey = dict(data.items() + {'city_name':city['name']}.items())
            
            # init headers
            headers_grades = self.init_headers()
            headers_grades['sign'] = self.sign(data, headers_grades)
            headers_grades.update({"Content-Length":len(json.dumps(data))})
            
            # get city grades
            self.crawl(city_grade_url, callback=self.city_page, method='POST',
                       data=json.dumps(data), headers=headers_grades, save=data_to_convey)
        
    
    @config(age=1 * 60)
    #@config(age=3 * 24 * 60 * 60)
    def city_page(self, response):
        
        # get city code
        city_code = response.save['area_code']
        city_name = response.save['city_name']
        
        # get city grades
        periods, grades = response.json['data'], []
        for period in periods: grades += period['grades']
            
        # get teacher grade by grade
        grade_url = self.host + "/_mock_/course/search"
        for grade in grades:
            
            data = {k:v for k,v in self.course_data.items()}
            grade_id, grade_name = grade['id'], grade['name']
            data.update({'cityName':city_name, 'areaCode':city_code})
            data.update({'gradeName':grade_name, 'gradeId':grade_id})
            
            # init headers
            headers_course = self.init_headers()
            headers_course['sign'] = self.sign(data, headers_course)
            headers_course.update({"Content-Length":len(json.dumps(data))})
            
            # get grade courses
            self.crawl(grade_url, callback=self.grade_page, method='POST', 
                       data=json.dumps(data), headers=headers_course, save=data)
        

    @config(age=1 * 60)
    #@config(age=3 * 24 * 60 * 60)
    def grade_page(self, response):
        
        # get request data
        page_size = response.save['limit']
        city_code = response.save['areaCode']
        city_name = response.save['cityName']
        grade_id  = response.save['gradeId']
        grade_name= response.save['gradeName']
        
        # get response data
        response_data = response.json['data']
        response_data = response_data['data']
        total_course = response_data['totalCount']
        page_no = response_data['pageIndex']
        courses = response_data['rows']
        
        # get course page by page
        grade_url = self.host + "/_mock_/course/search"
        for offset in range(int(math.ceil(total_course / float(page_size)))):
            if page_no > 1 or offset == 0: continue
                
            data = response.save
            data['page'] = offset + 1
            
            # init headers
            headers_course = self.init_headers()
            headers_course['sign'] = self.sign(data, headers_course)
            headers_course.update({"Content-Length":len(json.dumps(data))})
            
            # get grade courses
            self.crawl(grade_url, callback=self.grade_page, method='POST', 
                       data=json.dumps(data), headers=headers_course, save=data)
            
        # get teacher info
        for course in courses: 
            teachers = course['teachers']
            for teacher in teachers:
                teacher_id = teacher['teacherId']
                teacher_type = teacher['teacherType']
                
                # introduction request data prepare
                data_introduction = {
                    "areaCode":city_code,
                    "id":teacher_id,
                    "teacherType":teacher_type
                }
                data_introduction_to_save = {k:v for k,v in data_introduction.items()}
                data_introduction_to_save.update({'city_name': city_name})
                data_introduction_1 = "&".join(["=".join([k,v]) for k,v in data_introduction.items()])
                
                # init introduction headers
                headers_introduction = self.init_headers()
                headers_introduction.update({
                    "Content-Length":len(json.dumps(data_introduction)),
                })
                
                # get introduction
                headers_introduction['sign'] = self.sign(data_introduction, headers_introduction)
                introduction_url = self.host + "/_mock_/teacher/introduction"
                self.crawl(introduction_url, callback=self.teacher_intro_page, method='POST',
                           data=json.dumps(data_introduction), save=data_introduction_to_save, 
                           headers=headers_introduction)
                
                # evaluation request data prepare
                data_evaluation = { 
                    "areaCode":city_code,
                    "teacherId":teacher_id,
                    "teacherType":teacher_type,
                }
                
                # init evaluation headers
                headers_evaluation = self.init_headers()
                headers_evaluation.update({
                    "Content-Length":len(json.dumps(data_evaluation)),
                })
                
                # get evaluation
                headers_evaluation['sign'] = self.sign(data_evaluation, headers_evaluation)
                evaluation_url = self.host + "/_mock_/teacher/evaluation"
                self.crawl(evaluation_url, callback=self.teacher_eva_page, method='POST',
                           data=json.dumps(data_evaluation), save=data_evaluation,
                           headers=headers_evaluation)
            
        # assemble class info
        result = {
            "type": "course",
            "url": response.url,
            "city_code": city_code,
            "city_name": city_name,
            "grade_id": grade_id,
            "grade_name": grade_name,
            "courses": courses,
        }
                
        return result
        
   
    @config(priority=5)
    #@config(age=1 * 60)
    @config(age=3 * 24 * 60 * 60)
    def teacher_intro_page(self, response):
        if response.json['error_code'] != 0: return
        
        # get teacher id
        city_code   = response.save['areaCode']
        city_name   = response.save['city_name']
        teacher_id  = response.save['id']
        teacher_type= response.save['teacherType']
        
        # get response data
        response_data = response.json['data']
        
        # assemble evaluations
        result = {
            "type": "introduction",
            "url": response.url,
            "city_code": city_code,
            "city_name": city_name,
            "teacher_id": teacher_id,
            "teacher_type": teacher_type,
            "introduction": response_data,
        }
        
        return result
        
   
    #@config(priority=5)
    #@config(age=1 * 60)
    @config(age=3 * 24 * 60 * 60)
    def teacher_eva_page(self, response):
        if response.json['error_code'] != 0: return
        
        # get teacher id
        city_code = response.save['areaCode']
        teacher_id= response.save['teacherId']
        teacher_type= response.save['teacherType']
        
        # get response data
        response_data = response.json['data']
        avg_score = response_data['avg_score']
        tags = response_data['evaluate_tags']
        comments = response_data['evaluate_list']
        
        # assemble evaluations
        result = {
            "type": "evaluation",
            "url": response.url,
            "city_code": city_code,
            "teacher_id": teacher_id,
            "teacher_type": teacher_type,
            "score": avg_score,
            "tags": tags,
            "comments": comments,
        }
        
        return result
    
    
    # get default headers
    def init_headers(self):

        headers = {k:v for k,v in self.common_headers.items()}
        headers.update({
            "timestamp": str(self.timestamp()), 
            "nonce": self.nonce(), 
            "devid": self.devid(), 
        })
        
        return headers
    
    
    # generate timestamp
    def timestamp(self):
        
        return int(time.time()*1000)
    
    
    # generate unique user id
    def uuid(self):
        chars = self.digits + self.letters[:6]

        e = []
        for _ in range(36):
            offset = random.randint(0, len(chars)-1)
            char = chars[offset]
            e.append(char)

        # changing
        e[14] = '4'
        e[19] = chars[3 & ord(e[19]) | 8]
        e[8] = e[13] = e[18] = e[23] = ""

        return "".join(e)
    
    
    # generate device id 
    def devid(self):
        
        chars = self.digits + self.letters + self.letters.upper()
        
        e = ["q", "-"]
        for _ in range(26):
            offset = random.randint(0, len(chars)-1)
            char = chars[offset]
            e.append(char)
            
        return "".join(e)


    # generate _mock_ nonce 
    def nonce(self):

        timestamp = self.timestamp()
        return str(timestamp) + self.uuid()


    # generate encrypt data body
    def encrypt_obj(self, data, headers):
        headers = {k.lower():v for k,v in headers.items()}
        headers = {k:v for k,v in headers.items() if k in self.headers_list}

        # merge data and headers
        obj = {}
        obj.update(data)
        obj.update(headers)
        obj = [(k,str(v)) for k,v in obj.items()]
        obj = [(k,v) for k,v in obj if v != ""]

        # convert to str
        obj.sort()
        obj = "&".join(["=".join(pair) for pair in obj])

        return obj.encode('utf-8')


    # generate signature
    def sign(self, data, headers):

        # package data
        obj = self.encrypt_obj(data, headers)

        # generate signature
        private_key = self.private_key
        signature = hmac.new(private_key, obj, digestmod=hashlib.sha1)
        sign = signature.hexdigest().upper()

        return sign
        
        
        

