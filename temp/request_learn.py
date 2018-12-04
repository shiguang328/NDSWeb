import requests
from pprint import pprint
import json

USER_NAME = '496073473@qq.com'
PASSWORD = input('Please input the password: ')

# r = requests.get(url='http://localhost:5000')
r = requests.get(url='http://localhost:5000/api/v1/cars/', auth=(USER_NAME, PASSWORD))
print(r.status_code)  # 状态码
print(r.content)  # 内容 str格式
pprint(r.json())  # json解码
print(r.headers)  # headers
print(r.cookies)  # cookies
