import os
import json
import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# 1. 설정
KEY_INFO_STR = os.environ.get('GOOGLE_INDEXING_KEY')
ATOM_URL = 'https://www.omniscient.kr/atom.xml?redirect=false&start-index=1&max-results=150'
DAYS_TO_CHECK = 3 # 최근 3일 이내의 글만 전송

def get_recently_updated_urls():
    print(f"🔗 블로그에서 최근 {DAYS_TO_CHECK}일 이내에 작성/수정된 글을 찾습니다...")
    urls = []
    
    try:
        response = requests.get(ATOM_URL, timeout=15)
        root = ET.fromstring(response.content)
        ns = {'ns': 'http://www.w3.org/2005/Atom'}
        
        # 기준 시간: 현재 시간 - 3일
        cutoff_time = datetime.utcnow() - timedelta(days=DAYS_TO_CHECK)
        
        for entry in root.findall('ns:entry', ns):
            updated = entry.find('ns:updated', ns)
            if updated is None:
                continue
                
            # 시간 파싱 (밀리초 제거하여 안전하게 처리)
            time_str = updated.text[:19]
            updated_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
            
            # 3일 이내에 수정된 글만 합격!
            if updated_time >= cutoff_time:
                link = entry.find('ns:link[@rel="alternate"]', ns)
                if link is not None:
                    url = link.attrib['href'].split('?')[0].split('#')[0].strip()
                    urls.append(url)
                    
        return list(set(urls))
    except Exception as e:
        print(f"❌ 수집 중 오류 발생: {e}")
        return []

if __name__ == "__main__":
    if not KEY_INFO_STR:
        print("🚨 GOOGLE_INDEXING_KEY 환경 변수가 없습니다.")
        exit(1)
        
    # 최신 글만 수집
    target_urls = get_recently_updated_urls()
    
    if not target_urls:
        print(f"📭 최근 {DAYS_TO_CHECK}일 동안 작성/수정된 글이 없습니다. 구글을 호출하지 않고 종료합니다.")
        exit(0)
        
    print(f"✅ 총 {len(target_urls)}개의 최신 글을 구글에 전송합니다.")

    # 구글 인증
    try:
        KEY_INFO = json.loads(KEY_INFO_STR)
        scopes = ["https://www.googleapis.com/auth/indexing"]
        creds = service_account.Credentials.from_service_account_info(KEY_INFO, scopes=scopes)
    except Exception as e:
        print(f"🚨 구글 인증 오류: {e}")
        exit(1)

    # 구글 API 전송
    success_count = 0
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
        
        print(f"[{i+1}/{len(target_urls)}] 상태: {res.status_code} - {url}")
        
        if res.status_code == 200:
            success_count += 1
        elif res.status_code == 429:
            print("🚨 구글 할당량 초과! 전송을 멈춥니다.")
            break
        
        time.sleep(0.5)

    print(f"\n✨ 오늘 작업 완료! (성공: {success_count}개)")
