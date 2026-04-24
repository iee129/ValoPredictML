import requests
import time
import pandas as pd
import sys

# ==========================================
# 1. 설정 부분
# ==========================================
API_KEY = "HDEV-addcbe41-0c3e-4fba-82bf-59de04bbbb56" 
HEADERS = {"Authorization": API_KEY}
REGION = "ap"
PLATFORM = "pc"

target_players = [{"name": "Chrollo", "tag": "22222"}]
MATCH_COUNT = 10 

# ==========================================
# 2. 데이터 수집 함수 (강화된 버전)
# ==========================================

def get_match_ids(name, tag, count=10):
    """매치 리스트 가져오기 (실패 시 3번 재시도)"""
    url = f"https://api.henrikdev.xyz/valorant/v4/matches/{REGION}/{PLATFORM}/{name}/{tag}"
    params = {"mode": "competitive", "size": count}
    
    for attempt in range(3):
        try:
            print(f"🔍 [{name}#{tag}] 매치 목록 불러오는 중... (시도 {attempt+1}/3)")
            # 목록은 상대적으로 가벼우므로 timeout 60초
            response = requests.get(url, headers=HEADERS, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json().get('data', [])
                return [match['metadata']['match_id'] for match in data]
            elif response.status_code == 429:
                print("⚠️ 너무 빠릅니다! 30초 대기 후 다시 시도합니다...")
                time.sleep(30)
            else:
                print(f"❌ 서버 응답 에러: {response.status_code}")
        except Exception as e:
            print(f"⚠️ 연결 오류: {e}")
            time.sleep(10)
    return []

def extract_match_data(match_id, target_name, target_tag):
    """v4 매치 상세 데이터 추출 (무제한급 타임아웃 + 재시도 적용)"""
    url = f"https://api.henrikdev.xyz/valorant/v4/match/{REGION}/{match_id}"
    
    # 한 매치당 최대 5번까지 재시도 (서버가 응답을 줄 때까지)
    for attempt in range(5):
        try:
            # ★ 핵심: 타임아웃을 180초(3분)로 설정하여 서버가 큰 데이터를 다 만들 때까지 기다립니다.
            response = requests.get(url, headers=HEADERS, timeout=180)
            
            if response.status_code == 200:
                match_data = response.json().get('data', {})
                
                # --- 데이터 파싱 로직 (기존 유지) ---
                metadata = match_data.get('metadata', {})
                map_name = metadata.get('map', {}).get('name', 'Unknown')
                
                red_score = 0
                blue_score = 0
                rounds = match_data.get('rounds', [])
                for r in rounds:
                    winner = r.get('winning_team')
                    if winner == 'Red': red_score += 1
                    elif winner == 'Blue': blue_score += 1
                rounds_played = red_score + blue_score
                
                player_stats = {}
                for p in match_data.get('players', []):
                    if p.get('name', '').lower() == target_name.lower() and p.get('tag', '').lower() == target_tag.lower():
                        stats = p.get('stats', {})
                        player_stats['team'] = p.get('team_id', 'Unknown')
                        player_stats['kills'] = stats.get('kills', 0)
                        player_stats['deaths'] = stats.get('deaths', 0)
                        player_stats['assists'] = stats.get('assists', 0)
                        total_score = stats.get('score', 0)
                        player_stats['acs'] = round(total_score / rounds_played, 1) if rounds_played > 0 else 0
                        break

                return {
                    "Match_ID": match_id, "Player": f"{target_name}#{target_tag}", "Map": map_name,
                    "Total_Rounds": rounds_played, "Red_Score": red_score, "Blue_Score": blue_score,
                    "Player_Team": player_stats.get('team', 'Unknown'), "Kills": player_stats.get('kills', 0),
                    "Deaths": player_stats.get('deaths', 0), "Assists": player_stats.get('assists', 0),
                    "ACS": player_stats.get('acs', 0)
                }

            elif response.status_code == 429:
                print(f"   ⚠️ 속도 제한 발생! 20초간 휴식 후 재시도 합니다...")
                time.sleep(20)
            else:
                print(f"   ❌ 매치 {match_id} 오류 (코드: {response.status_code})")
                
        except Exception as e:
            print(f"   ⚠️ 연결 지연/오류: {e}. 15초 후 재시도...")
            time.sleep(15)
            
    return None

# ==========================================
# 3. 메인 파이프라인
# ==========================================
def main():
    print("🚀 [완주 모드] 발로란트 전적 데이터 수집 시작!")
    collected_data = []
    
    for player in target_players:
        p_name, p_tag = player['name'], player['tag']
        match_ids = get_match_ids(p_name, p_tag, count=MATCH_COUNT)
        
        if not match_ids:
            print(f"❌ {p_name}의 매치 목록을 가져오지 못했습니다.")
            continue
            
        print(f"✅ 총 {len(match_ids)}개의 매치를 찾았습니다. 하나씩 정성껏 수집합니다.")
        
        for idx, mid in enumerate(match_ids):
            print(f"📦 [{idx + 1}/{len(match_ids)}] 경기 수집 중... (ID: {mid})")
            
            match_info = extract_match_data(mid, p_name, p_tag)
            
            if match_info:
                collected_data.append(match_info)
                print(f"   >> ✨ 성공! (KDA: {match_info['Kills']}/{match_info['Deaths']})")
            else:
                print(f"   >> ❌ 이 경기는 끝내 실패했습니다. (건너뜀)")
                
            # ★ 중요: v4는 너무 무거워서 수집 성공 후에도 10초는 쉬어줘야 서버가 안 화냅니다.
            if idx < len(match_ids) - 1:
                print("☕ 서버 과부하 방지를 위해 10초간 대기 중...")
                time.sleep(10)

    # 저장 로직
    df = pd.DataFrame(collected_data)
    if not df.empty:
        save_filename = "valorant_match_history.csv"
        df.to_csv(save_filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ 수집 완료! 총 {len(df)}경기 데이터가 '{save_filename}'에 저장되었습니다.")
    else:
        print("\n❌ 최종 수집된 데이터가 없습니다.")

if __name__ == "__main__":
    main()