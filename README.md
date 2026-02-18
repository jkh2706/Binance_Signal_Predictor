# Binance Signal Predictor 🚀

**바이낸스 과거 차트 데이터를 분석하여 가격을 예측하고 투자 여부를 결정하는 알고리즘 프로젝트**

이 프로젝트는 바이낸스(Binance) 거래소의 과거 OHLCV(Open, High, Low, Close, Volume) 데이터를 수집하고, 이를 다양한 지표와 알고리즘으로 분석하여 최적의 매매 타이밍을 예측하는 것을 목표로 합니다.

## 🛠️ 주요 기능 (예정)
1. **과거 데이터 수집:** 바이낸스 REST API를 사용하여 특정 기간의 K-라인(봉) 데이터를 자동으로 가져옵니다.
2. **기술적 지표 분석:** 이동평균선(MA), RSI, MACD, 볼린저 밴드 등 다양한 보조지표를 계산합니다.
3. **가격 예측 알고리즘:** 머신러닝 또는 통계적 모델을 활용하여 향후 가격 흐름을 예측합니다.
4. **투자 결정 로직:** 예측된 데이터를 바탕으로 매수/매도 신호를 생성합니다.

## 📂 프로젝트 구조
- `data_fetcher.py`: 바이낸스 API를 통한 과거 데이터 수집 모듈
- `analyzer.py`: 수집된 데이터 분석 및 기술적 지표(RSI, MACD, BB, OBV 등) 계산 모듈
- `macro_fetcher.py`: Yahoo Finance API를 통해 달러 인덱스(DXY), 미국채 금리, 나스닥 등 거시 경제 지표를 수집하고 결합하는 모듈
- `predictor.py`: 인공지능(Random Forest)을 활용하여 기술적 지표와 매크로 지표를 통합 학습하고 모델을 저장하는 모듈
- `realtime_predictor.py`: 현재 시장 데이터를 가져와 저장된 모델로 4시간 뒤 상승 확률을 실시간 예측하는 실전 모듈
- `backtester.py`: **(신규)** 수정된 ROE 공식과 수수료 로직이 반영된 최종 백테스팅 모듈
- `requirements.txt`: 필요한 라이브러리 목록

## ⚙️ 설치 및 실행 방법
1. `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 본인의 API 키와 시트 ID를 입력하세요.
2. 필요한 라이브러리 설치: `pip install -r requirements.txt`
3. 모델 학습: `python3 train_xrp_v3.py`
4. 백테스터 실행: `python3 backtester.py`
5. 실시간 예측 실행: `python3 xrp_realtime_predictor.py`

---
*본 프로젝트는 기훈님과 AI 비서 클로이가 함께 만들어가는 프로젝트입니다.* ✨
