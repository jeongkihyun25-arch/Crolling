import os
import json
import requests
import xml.etree.ElementTree as ET
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import time

# 1. 환경 설정
# GitHub Secrets에서 가져온 JSON 데이터를 처리합니다.
service_account_info = json.loads(os.environ.get('GOOGLE_INDEXING_KEY'))
BLOG_ATOM_URL = 'https://www.omniscient.kr/atom.xml?redirect=false&start-index=1&max-results=500'

def get_urls_from_atom(atom_url):
    print("블로그 피드에서 주소를 수집 중입니다...")
    response = requests.get(atom_url)
    root = ET.fromstring(response.content)
    ns = {'ns': 'http://www.w3.org/2005/Atom'}
    urls = []
    for entry in root.findall('ns:entry', ns):
        link = entry.find('ns:link[@rel="alternate"]', ns)
        if link is not None:
            urls.append(link.attrib['href'])
    return urls

def send_indexing_request(url, credentials):
    endpoint = "https://indexing.googleapis.com/v3/urlNotifications:publish"
    if not credentials.valid:
        credentials.refresh(Request())
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {credentials.token}"
    }
    data = {"url": url, "type": "URL_UPDATED"}
    response = requests.post(endpoint, json=data, headers=headers)
    return response.status_code

if __name__ == "__main__":
    scopes = ["https://www.googleapis.com/auth/indexing"]
    creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
    
    blog_urls = get_urls_from_atom(BLOG_ATOM_URL)
    print(f"총 {len(blog_urls)}개의 글을 발견했습니다.")
    
    for i, url in enumerate(blog_urls):
        status = send_indexing_request(url, creds)
        print(f"[{i+1}/{len(blog_urls)}] {status} - {url}")
        time.sleep(0.5)
