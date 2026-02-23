import requests
import json
import hashlib

headers = {'Content-Type':'application/json;charset=utf-8'}

def get_token():
    data = '{"username": "Rizvi", "password": "fd5c1cf04c8e68ded43719f50fa81fda"}'
    response = requests.post("https://cloud.minewtag.com/apis/action/login", data=data, headers=headers)
    token = response.json()['data']['token']
    print(token)
    return token


def get_token_refurbished():
    headers = {'Content-Type':'application/json;charset=utf-8'}
    username = "Rizvi"
    password = "Minew123456"
    password_md5 = hashlib.md5(password.encode("utf-8")).hexdigest()
    data = {"username": username, "password": password_md5}
    response = requests.post("https://cloud.minewtag.com/apis/action/login", data=data, headers=headers)
    responsejson = response.json()
    token = data.get("data", {}).get("token")
    print(token)
    return token
