import pandas as pd
import json
import os

def generate_report():
    base_path = "."
    trades_path = os.path.join(base_path, "virtual_trades.csv")
    state_path = os.path.join(base_path, "virtual_bot_state.json")
    
    report = "📊 **클로이의 XRP 가상 트레이딩 정기 보고** ✨\n\n"
    
    # 1. 현재 상태 확인
    if os.path.exists(state_path):
        try:
            with open(state_path, 'r') as f:
                state = json.load(f)
                report += f"🔹 **현재 포지션:** {state.get('position', 'UNKNOWN')}\n"
                report += f"🔹 **현재 잔고:** ${state.get('balance', 0):,.2f}\n"
                report += f"🔹 **마지막 업데이트:** {state.get('last_update', 'N/A')}\n\n"
        except Exception as e:
            report += f"⚠️ 상태 파일 읽기 오류: {e}\n\n"
    
    # 2. 최근 트레이딩 성과
    if os.path.exists(trades_path):
        try:
            df = pd.read_csv(trades_path)
            if not df.empty:
                # 한글 컬럼명 매핑
                # 시간(KST),액션,심볼,포지션,가격,수익률(ROE),잔고(XRP)
                last_5 = df.tail(5)
                report += "📈 **최근 거래 내역 (최신 5건):**\n"
                for _, row in last_5.iterrows():
                    report += f"- {row['시간(KST)']}: {row['액션']} ({row['포지션']}) | 가격: ${row['가격']} | 수익률: {row['수익률(ROE)']}\n"
                
                # 수익률 문자열에서 '%' 제거 후 숫자로 변환하여 계산
                df['pnl_num'] = df['수익률(ROE)'].str.replace('%', '').astype(float)
                total_pnl = df[df['액션'].str.contains('EXIT', na=False)]['pnl_num'].sum()
                
                report += f"\n💰 **누적 성과 (종료된 거래 기준):**\n"
                report += f"- 총 누적 수익률: {total_pnl:.2f}%\n"
            else:
                report += "ℹ️ 아직 기록된 거래 내역이 없습니다.\n"
        except Exception as e:
            report += f"⚠️ 거래 내역 분석 오류: {e}\n"
    else:
        report += "⚠️ 거래 내역 파일을 찾을 수 없습니다.\n"

    report += "\n🚀 클로이는 오늘도 열심히 학습하며 시장을 감시하고 있어요!"
    return report

if __name__ == "__main__":
    try:
        print(generate_report())
    except Exception as e:
        print(f"리포트 생성 중 치명적 오류: {e}")
