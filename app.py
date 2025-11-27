import os
import requests
import yaml
import json
import time
import re
import concurrent.futures
from datetime import datetime, timedelta, timezone
import pytz
from flask import Flask, render_template, jsonify
from dateutil import parser as date_parser

# 스케줄러
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import webbrowser
from threading import Timer

app = Flask(__name__)

# --- 설정 ---
GITHUB_REPO_API = "https://api.github.com/repos/ccfddl/ccf-deadlines/contents/conference"
DATA_FILE = "conferences_data.json"      # [변경] 이제 여기엔 RAW 데이터가 들어갑니다.
LOG_FILE = "update_log.json"

CATEGORY_CONFIG = {
    'AI': {'folder': 'AI', 'name': 'Artificial Intelligence'},
    'CG': {'folder': 'CG', 'name': 'Computer Graphics'}, 
    'CT': {'folder': 'CT', 'name': 'Computing Theory'},
    'DB': {'folder': 'DB', 'name': 'Database / Data Mining / IR'},
    'DS': {'folder': 'DS', 'name': 'Computer Arch / Storage'},
    'HI': {'folder': 'HI', 'name': 'Computer-Human Interaction'},
    'MX': {'folder': 'MX', 'name': 'Interdisciplinary / Emerging'},
    'SE': {'folder': 'SE', 'name': 'Software Engineering'},
    'SC': {'folder': 'SC', 'name': 'Network & Security'},
    'NW': {'folder': 'NW', 'name': 'Computer Networks'}
}

# =========================================================
# 1. [핵심] 날짜 계산 로직 (Reusable Helper)
# =========================================================
def calculate_utc_deadline(raw_date_str, raw_tz_str):
    """
    RAW 문자열(날짜, 타임존)을 받아서 -> 계산된 UTC datetime 객체를 반환
    """
    try:
        if not raw_date_str or raw_date_str == 'TBA':
            return None

        # 1. 날짜 파싱
        deadline_dt = date_parser.parse(raw_date_str)
        
        # 2. 타임존 오프셋 계산
        tz_str = str(raw_tz_str).upper() if raw_tz_str else 'UTC'
        offset_hours = 0
        
        if 'AOE' in tz_str: offset_hours = -12
        elif 'UTC' in tz_str or 'GMT' in tz_str:
            match = re.search(r'(?:UTC|GMT)\s?([+-]?\d+)', tz_str)
            offset_hours = int(match.group(1)) if match else 0
        elif 'PST' in tz_str: offset_hours = -8
        elif 'PDT' in tz_str: offset_hours = -7
        elif 'EST' in tz_str: offset_hours = -5
        elif 'EDT' in tz_str: offset_hours = -4
        elif 'JST' in tz_str or 'KST' in tz_str: offset_hours = 9
        
        # 3. Timezone 객체 생성 및 적용
        tz_obj = timezone(timedelta(hours=offset_hours))
        
        if deadline_dt.tzinfo is None:
            deadline_aware = deadline_dt.replace(tzinfo=tz_obj)
        else:
            deadline_aware = deadline_dt.astimezone(tz_obj)
        
        # 4. UTC로 변환하여 반환
        return deadline_aware.astimezone(pytz.utc)

    except Exception:
        return None

# =========================================================
# 2. 데이터 수집 및 RAW 저장 (Extraction)
# =========================================================
def extract_conference_info(conf, sub_code, full_name):
    """
    YAML을 분석하여 '가장 적절한 라운드'의 RAW 데이터를 추출합니다.
    (여기서는 계산된 날짜를 저장하지 않고, 원본 문자열을 저장합니다)
    """
    try:
        if not conf.get('sub'): conf['sub'] = sub_code
        confs_list = conf.get('confs', [])
        
        # 기본 골격
        entry = {
            "id": conf.get('title'),
            "title": conf.get('title'),
            "description": conf.get('description'),
            "sub": conf.get('sub'),
            "sub_name": full_name,
            "rank": conf.get('rank', {}).get('ccf', 'N'),
            # --- [변경] RAW 데이터 저장 필드 ---
            "raw_deadline": None,
            "raw_timezone": None,
            "raw_place": "TBA",
            "year": "N/A",
            # ----------------------------------
            "has_future_round": False # 나중에 필터링을 위한 플래그
        }

        if not confs_list: return entry

        now = datetime.now(pytz.utc)
        
        # 여러 라운드 중 가장 가까운 미래의 라운드를 찾음
        best_round = None
        
        for c in confs_list:
            timeline = c.get('timeline', [])
            raw_tz = c.get('timezone', 'UTC') # 타임존은 conf 레벨에 있음
            
            for t in timeline:
                raw_date = t.get('deadline', 'TBA')
                
                # 계산기를 돌려서 미래인지 확인 (선택을 위해 계산은 필요함)
                utc_dt = calculate_utc_deadline(raw_date, raw_tz)
                
                if utc_dt and utc_dt > now:
                    # 미래 라운드 발견! 이 정보를 저장 후보로 선정
                    entry["year"] = c.get('year')
                    entry["raw_deadline"] = raw_date  # <--- 변환 안 하고 그대로 저장
                    entry["raw_timezone"] = raw_tz    # <--- 변환 안 하고 그대로 저장
                    entry["raw_place"] = c.get('place', 'TBA')
                    entry["has_future_round"] = True
                    best_round = True
                    break # 타임라인 루프 탈출
            
            if best_round:
                break # 연도 루프 탈출
        
        return entry

    except Exception:
        return None

def fetch_single_yaml(url, sub_code, full_name):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return []
        confs = yaml.safe_load(resp.text)
        if isinstance(confs, dict): confs = [confs]
        
        results = []
        for conf in confs:
            processed = extract_conference_info(conf, sub_code, full_name)
            if processed: results.append(processed)
        return results
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []

def fetch_conference_data(force_refresh=False):
    # 1. (기존 로직) 강제 새로고침이 아니면 로컬 파일 우선 사용
    if not force_refresh and os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data: # 데이터가 있을 때만 리턴
                    return data
        except Exception:
            pass

    print("🌐 Fetching fresh data from GitHub...")
    all_data = []
    tasks = []
    headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {os.getenv('GITHUB_TOKEN', '')}"}
    
    # API 제한 확인용 플래그
    rate_limit_hit = False

    for sub_code, config in CATEGORY_CONFIG.items():
        try:
            resp = requests.get(f"{GITHUB_REPO_API}/{config['folder']}", headers=headers)
            
            # [추가] API 제한 걸렸는지 확인
            if resp.status_code == 403 or resp.status_code == 429:
                print(f"❌ [Error] GitHub API Rate Limit Hit! (Category: {sub_code})")
                rate_limit_hit = True
                break
                
            if resp.status_code == 200:
                for f in resp.json():
                    if f['name'].endswith('.yml'):
                        tasks.append((f['download_url'], sub_code, config['name']))
        except Exception as e: 
            print(f"Error fetching list: {e}")

    # API 제한에 걸리지 않았을 때만 상세 다운로드 진행
    if not rate_limit_hit and tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(fetch_single_yaml, u, s, n) for u, s, n in tasks]
            for f in concurrent.futures.as_completed(futures):
                all_data.extend(f.result())

    # 3. [핵심 수정] 데이터가 정상적으로 모였을 때만 저장
    if all_data:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        save_update_time()
        print(f"✅ Successfully updated {len(all_data)} conferences.")
        return all_data
    
    else:
        # 실패했거나 빈 데이터라면
        print("⚠️ Warning: Fetched data is empty. (Maybe Rate Limit?)")
        
        # 기존 로컬 파일이라도 있으면 그걸 반환해서 화면이 백지가 되는 것 방지
        if os.path.exists(DATA_FILE):
            print("🔄 Falling back to existing local data...")
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        
        return []

# 로그 관련 함수 (기존 동일)
def get_last_update_time():
    if not os.path.exists(LOG_FILE): return None
    try:
        with open(LOG_FILE, 'r') as f:
            return datetime.fromisoformat(json.load(f).get("last_success", ""))
    except: return None

def save_update_time():
    try:
        with open(LOG_FILE, 'w') as f:
            json.dump({"last_success": datetime.now().isoformat()}, f)
    except: pass

def scheduled_update_job():
    last = get_last_update_time()
    if not last or (datetime.now() - last).days >= 7:
        print("⏰ Auto-updating conferences...")
        fetch_conference_data(force_refresh=True)

# =========================================================
# 3. API 서빙 (Serving & Calculation)
# =========================================================
@app.route('/api/conferences')
def get_conferences_api():
    """
    저장된 RAW 데이터를 읽어와서, 
    API 응답을 줄 때 실시간으로 UTC 시간을 계산해서 내려줍니다.
    """
    raw_data = fetch_conference_data() # 메모리 or 파일 로드
    response_data = []
    
    now = datetime.now(pytz.utc)

    for item in raw_data:
        # 1. RAW 데이터 읽기
        raw_date = item.get('raw_deadline')
        raw_tz = item.get('raw_timezone')
        
        # 2. 실시간 계산
        utc_dt = calculate_utc_deadline(raw_date, raw_tz)
        
        # 3. 프론트엔드용 객체 생성
        # (기존 프론트엔드 코드와 호환되도록 필드명 매핑)
        final_obj = {
            "id": item['id'],
            "title": item['title'],
            "description": item['description'],
            "sub": item['sub'],
            "sub_name": item['sub_name'],
            "rank": item['rank'],
            "place": item.get('raw_place', 'TBA'),
            "year": item.get('year'),
            
            # 계산된 결과 주입
            "deadline": utc_dt.isoformat() if utc_dt else None,
            
            # 미래인지 아닌지 최종 판단 (저장 시점과 서빙 시점이 다를 수 있으므로)
            "is_active": (utc_dt > now) if utc_dt else False
        }
        
        response_data.append(final_obj)
        
    return jsonify(response_data)

def open_browser():
    """서버가 시작된 후 1.5초 뒤에 브라우저를 엽니다."""
    print("🌍 Opening browser...")
    webbrowser.open_new("http://127.0.0.1:5000")

@app.route('/api/refresh')
def refresh_data():
    fetch_conference_data(force_refresh=True)
    return jsonify({"status": "success"})

@app.route('/')
def index(): return render_template('index.html')

if __name__ == '__main__':
    # 1. 스케줄러 설정
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=scheduled_update_job, trigger="cron", day_of_week='sat', hour=9)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    
    # 2. [추가] 브라우저 자동 실행 타이머
    # 서버가 완전히 켜질 시간을 주기 위해 1.5초 딜레이를 줍니다.
    # (debug=True 모드에서는 리로더 때문에 두 번 열릴 수 있는데, 이를 방지하려면 환경변수 체크가 필요하지만 일단 간단히 구현합니다)
    Timer(1.5, open_browser).start()

    print("🚀 Server started with Scheduler (Every Saturday 9:00 AM)")
    app.run(debug=True, host='0.0.0.0', port=5000)