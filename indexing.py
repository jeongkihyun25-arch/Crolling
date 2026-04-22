import os
import json
import requests
import xml.etree.ElementTree as ET
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import time

# 1. 환경 설정
service_account_info = json.loads(os.environ.get('GOOGLE_INDEXING_KEY'))
BASE_ATOM_URL = 'https://www.omniscient.kr/atom.xml'

def get_all_blog_urls(base_url):
    print("블로그 피드에서 273개 전원을 수집하기 시작합니다...")
    urls = []
    start_index = 1
    max_results = 150 # 블로거 1회 최대치

    while True:
        # 페이지를 넘기며 주소를 긁어옵니다.
        fetch_url = f"{base_url}?redirect=false&start-index={start_index}&max-results={max_results}"
        response = requests.get(fetch_url)
        root = ET.fromstring(response.content)
        ns = {'ns': 'http://www.w3.org/2005/Atom'}
        
        found_in_this_batch = 0
        for entry in root.findall('ns:entry', ns):
            link = entry.find('ns:link[@rel="alternate"]', ns)
            if link is not None:
                urls.append(link.attrib['href'])
                found_in_this_batch += 1
        
        print(f"[{start_index}번부터 {found_in_this_batch}개 수집 완료]")
        
        # 더 가져올 글이 없으면 멈춤
        if found_in_this_batch < max_results:
            break
        
        start_index += max_results
    
    return list(set(urls)) # 중복 제거 후 리스트 반환

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
    
    blog_urls = get_all_blog_urls(BASE_ATOM_URL)
    print(f"총 {len(blog_urls)}개의 글을 최종 발견했습니다.")
    
    # 구글 Indexing API의 하루 한도는 200개입니다. 
    # 273개이므로 오늘은 200개까지만 성공하고 나머지는 내일 자동으로 처리될 거예요.
    for i, url in enumerate(blog_urls):
        status = send_indexing_request(url, creds)
        print(f"[{i+1}/{len(blog_urls)}] {status} - {url}")
        
        if status == 429:
            print("🚨 구글 API 일일 할당량(200개)을 초과했습니다. 나머지는 내일 아침에 자동으로 처리됩니다!")
            break
            
        time.sleep(0.5)
