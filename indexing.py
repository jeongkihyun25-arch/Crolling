import os
import json
import requests
import time
from datetime import datetime
import xml.etree.ElementTree as ET
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# 1. 설정
KEY_INFO = json.loads(os.environ.get('GOOGLE_INDEXING_KEY'))
# 모든 글을 가져오기 위해 max-results=500 추가
ATOM_URL = 'https://www.omniscient.kr/atom.xml?redirect=false&start-index=1&max-results=500'

def get_all_urls():
    print("🔗 구글 전송을 위해 모든 URL 수집 중...")
    response = requests.get(ATOM_URL)
    root = ET.fromstring(response.content)
    ns = {'ns': 'http://www.w3.org/2005/Atom'}
    urls = []
    for entry in root.findall('ns:entry', ns):
        link = entry.find('ns:link[@rel="alternate"]', ns)
        if link is not None:
            urls.append(link.attrib['href'])
    return list(set(urls))

if __name__ == "__main__":
    # 구글 인증
    scopes = ["https://www.googleapis.com/auth/indexing"]
    creds = service_account.Credentials.from_service_account_info(KEY_INFO, scopes=scopes)
    
    all_urls = get_all_urls()
    total_count = len(all_urls)
    print(f"✅ 총 {total_count}개의 글을 발견했습니다.")

    # --- 순환 로직 (구글 버전: 하루 200개) ---
    day_of_year = datetime.now().timetuple().tm_yday
    # 200개씩 끊어서 순환
    start_index = (day_of_year * 200) % total_count
    target_urls = (all_urls + all_urls)[start_index : start_index + 200]
    # ---------------------------------------

    print(f"📅 오늘 전송 범위: {start_index + 1}번부터 최대 200개")

    for i, url in enumerate(target_urls):
        if not creds.valid:
            creds.refresh(Request())
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds.token}"
        }
        data = {"url": url, "type": "URL_UPDATED"}
        
        res = requests.post("https://indexing.googleapis.com/v3/urlNotifications:publish", 
                            json=data, headers=headers)
        
        print(f"[{i+1}/200] {res.status_code} - {url}")
        
        if res.status_code == 429:
            print("🚨 구글 할당량 초과! 내일 이어서 진행합니다.")
            break
        
        time.sleep(0.3)

    print("\n✅ 오늘치 구글 순환 작업 완료!")
