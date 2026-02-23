import asyncio
import sys
import os
import json
import logging
import socket
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from dotenv import load_dotenv
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException
import subprocess

# =========================================================
# 1) 설정
# =========================================================
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")

LOG_FILE = "trades_ws_v2.csv"
STATE_FILE = "trades_ws_v2_state.json"

# REST 백필 주기(초): WS 누락 안전망
BACKFILL_INTERVAL = 60

CSV_COLUMNS = [
    "시간(KST)", "심볼", "포지션방향",
    "매수/매도", "수량", "가격", "실현손익",
    "수수료", "수수료자산",
    "포지션수량", "평균진입가",
    "레버리지", "마진타입",
    "마진자산", "포지션마진", "미실현손익",
    "손절가(USD)", "익절가(USD)", "손익비(R)",
    "order_id", "trade_id",
]

# =========================================================
# 2) 로깅 / 파일 준비
# =========================================================
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logger_error.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def ensure_log_file():
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
        logging.info(f"신규 로그 파일 생성: {LOG_FILE}")
        return

    # 기존 파일이 있을 때 컬럼 구조 확인
    try:
        existing = pd.read_csv(LOG_FILE, nrows=0)
        existing_cols = list(existing.columns)
    except Exception as e:
        logging.error(f"기존 로그 파일 헤더를 읽는 중 오류 발생: {e}")
        backup_name = f"{LOG_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            os.rename(LOG_FILE, backup_name)
            logging.warning(f"손상된 로그 파일을 백업으로 이동: {backup_name}")
        except Exception as e2:
            logging.error(f"로그 파일 백업 실패: {e2}")
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
        logging.info(f"신규 로그 파일 생성: {LOG_FILE}")
        return

    if existing_cols == CSV_COLUMNS:
        logging.info(f"기존 로그 파일 사용: {LOG_FILE}")
        return

    # 컬럼 구조가 바뀐 경우
    backup_name = f"{LOG_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        os.rename(LOG_FILE, backup_name)
        logging.warning(f"컬럼 변경으로 백업 후 재생성: {backup_name}")
    except Exception as e:
        logging.error(f"로그 파일 백업 실패: {e}")

    df = pd.DataFrame(columns=CSV_COLUMNS)
    df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
    logging.info(f"신규 로그 파일 생성: {LOG_FILE}")

# =========================================================
# 2.5) 리포트 자동 생성 트리거 (Debounce)
# =========================================================
class ReportTrigger:
    def __init__(self, debounce_sec=5.0):
        self.debounce_sec = debounce_sec
        self._timer_task = None
    
    def schedule(self, loop):
        """체결 이벤트 시 호출 (Main Loop에서 실행됨)"""
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        
        self._timer_task = loop.create_task(self._run_report())

    async def _run_report(self):
        try:
            await asyncio.sleep(self.debounce_sec)
            logging.info("리포트 자동 생성 시작...")
            # subprocess (blocking but short for launching cmd, or use create_subprocess_exec)
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "binance_report_ws_v2.py",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                logging.info(f"리포트 생성 완료")
            else:
                logging.error(f"리포트 생성 실패: {stderr.decode()}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"리포트 트리거 오류: {e}")

# =========================================================
# 3) Async Journal Class
# =========================================================
class AsyncTradeJournal:
    """
    Asyncio 기반의 Trade Journal.
    - 웹소켓 수신 -> 큐 -> 처리(스냅샷+CSV기록)
    - 주기적 백필 작업
    """
    def __init__(self, client: AsyncClient, log_file: str):
        self.client = client
        self.log_file = log_file
        self._loop = asyncio.get_running_loop()
        
        # Async 제어
        self._queue = asyncio.Queue(maxsize=10000)
        self._stop_event = asyncio.Event()
        self._file_executor = ThreadPoolExecutor(max_workers=1)
        
        # 상태 관리
        self._symbol_info: dict[str, dict] = {} # contractSize 캐시
        self._last_trade_id: dict[str, int] = {}
        self._last_event_ts: dict[str, int] = {}
        self._seen_symbols: set[str] = set()
        
        self._report_trigger = ReportTrigger()
        
        self._load_state()

    def _load_state(self):
        if not os.path.exists(STATE_FILE):
            # State file missing, try CSV recovery
            if os.path.exists(self.log_file):
                self._recover_state_from_csv()
            return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._last_trade_id = {k: int(v) for k, v in data.get("last_trade_id", {}).items()}
            self._last_event_ts = {k: int(v) for k, v in data.get("last_event_ts", {}).items()}
            self._seen_symbols.update(self._last_trade_id.keys())
            self._seen_symbols.update(self._last_event_ts.keys())
            logging.info(f"STATE 로드 완료: symbols={len(self._last_trade_id)}")
        except Exception as e:
            logging.warning(f"STATE 로드 실패(csv 복구 시도): {e}")
            self._recover_state_from_csv()

        # 만약 로드/복구 후에도 비어있는데 파일은 있다면? -> 한 번 더 체크
        if not self._last_trade_id and os.path.exists(self.log_file):
            self._recover_state_from_csv()

    def _recover_state_from_csv(self):
        """
        State 파일이 없거나 깨졌을 때, CSV를 읽어서 마지막 trade_id를 복원
        """
        if not os.path.exists(self.log_file):
            return

        logging.info(f"CSV({self.log_file})에서 상태 복구 시작...")
        try:
            # 파일이 매우 클 수 있으므로 청크 단위로 읽거나, tail만 읽는 게 좋지만
            # 여기서는 pandas로 필요한 컬럼만 읽어서 그룹화 (메모리 주의)
            # trade_id 정렬을 위해 전체 스캔 필요할 수 있음.
            # 개선: tail -n 10000 등으로 최근 것만 봐도 되지만, 공백이 길었을 수 있음.
            # 안전하게 전체 로드 (메모리가 허용된다는 가정)
            # trade_id, symbol, 시간(KST) 정도만 로드
            use_cols = ["심볼", "trade_id", "시간(KST)"]
            
            # 헤더 확인
            header_df = pd.read_csv(self.log_file, nrows=0)
            available_cols = set(header_df.columns)
            if not set(use_cols).issubset(available_cols):
               logging.warning("CSV 헤더가 달라서 복구 불가")
               return

            # 전체 읽기 (dtype 지정)
            df = pd.read_csv(self.log_file, usecols=use_cols, dtype={"trade_id": float})
            df = df.dropna(subset=["trade_id"])
            
            if df.empty:
                return

            # 심볼별 max trade_id
            g = df.groupby("심볼")["trade_id"].max()
            for sym, tid in g.items():
                self._last_trade_id[sym] = int(tid)
                self._seen_symbols.add(sym)
            
            logging.info(f"CSV 복구 완료: {len(self._last_trade_id)}개 심볼 상태 복원됨")
            
            # event_ts는 정확히 알 수 없으니(CSV엔 KST 문자열만 있음),
            # 대략 현재 시간 - (오래전) 으로 잡거나, 
            # 사실 backfill은 trade_id 기준으로 중복 체크하므로 last_event_ts가 아주 옛날이어도 
            # trade_id > last_trade_id 인 것만 가져오면 됨.
            # 다만 startTime 파라미터 최적화를 위해...
            # 그냥 0으로 두면 API가 허용하는 가장 옛날부터 가져오려 할 텐데, 
            # binance는 startTime 없으면 '최근' 기준임. -> startTime 명시 필요하면 곤란.
            # -> trade_id 기반 fetching은 binance API에서 fromId 지원하나? 
            # futures_coin_account_trades: symbol, startTime, endTime, fromId, limit
            # fromId를 쓰면 좋지만, 여기 코드는 startTime 기반으로 짜여져 있음.
            # CSV의 '시간(KST)'를 파싱해서 ts로 변환해 넣어주는 게 좋음.
            
            # 시간 파싱 시도
            df["ts"] = pd.to_datetime(df["시간(KST)"], errors="coerce")
            g_time = df.groupby("심볼")["ts"].max()
            for sym, t_val in g_time.items():
                if pd.notna(t_val):
                    # ms 단위
                    self._last_event_ts[sym] = int(t_val.timestamp() * 1000)

        except Exception as e:
            logging.error(f"CSV 상태 복구 실패: {e}")

    def _save_state(self):
        # 잦은 I/O 방지를 위해 별도 executor나, 
        # 혹은 여기서는 간단히 동기 저장(파일이 작으므로)을 하되 
        # 너무 자주 불리지 않게 주의 or 비동기 처리 가능.
        # 여기서는 executor 사용
        try:
            data = {
                "last_trade_id": self._last_trade_id,
                "last_event_ts": self._last_event_ts,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            # 비동기적으로 실행하지 않으면 loop가 멈칫할 수 있음
            # 다만 상태 파일은 작아서 큰 문제는 없음.
            # 안전하게 executor 사용
            self._file_executor.submit(self._write_json, STATE_FILE, data)
        except Exception as e:
            logging.warning(f"STATE 저장 실패(무시): {e}")

    def _write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def get_contract_size(self, symbol: str) -> float:
        if symbol in self._symbol_info:
            return float(self._symbol_info[symbol].get("contractSize", 0.0))

        # 캐시 없으면 조회
        # 전체 교환정보를 가져오는 건 무거우니, 플래그를 두거나 한 번만 실행
        if not self._symbol_info:
            try:
                info = await self.client.futures_coin_exchange_info()
                for s in info.get("symbols", []):
                    sym = s.get("symbol")
                    if sym:
                        self._symbol_info[sym] = {"contractSize": float(s.get("contractSize", 0.0))}
            except Exception as e:
                logging.error(f"Exchange Info 조회 실패: {e}")
        
        data = self._symbol_info.get(symbol)
        return float(data.get("contractSize", 0.0)) if data else 0.0

    async def get_position_snapshot(self, symbol: str) -> Dict:
        try:
            # v1: client.futures_coin_position_information() -> 전체 조회
            # v2: 특정 심볼만 필터링 가능하면 좋으나, binance API가 보통 전체 리턴
            positions = await self.client.futures_coin_position_information()
            target = None
            for p in positions:
                if p["symbol"] == symbol:
                    target = p
                    break
            
            if target:
                qty = float(target["positionAmt"])
                entry = float(target["entryPrice"])
                return {
                    "qty": qty,
                    "entry": entry,
                    "upnl": float(target["unRealizedProfit"]),
                    "lev": float(target["leverage"]),
                    "margin_type": target["marginType"],
                    "isolated_margin": float(target["isolatedMargin"]),
                    "margin_asset": target.get("marginAsset", ""),
                    "position_initial_margin": float(target.get("positionInitialMargin", 0.0)),
                    # TP/SL은 별도 계산 필요
                    "sl": None,
                    "tp": None
                }
            return self._empty_position()
        except Exception as e:
            logging.error(f"[{symbol}] 포지션 조회 실패: {e}")
            return self._empty_position()

    def _empty_position(self):
        return {
            "qty": 0.0, "entry": 0.0, "upnl": 0.0, "lev": 1.0,
            "margin_type": "cross", "isolated_margin": 0.0,
            "margin_asset": "", "position_initial_margin": 0.0,
            "sl": None, "tp": None,
        }

    async def get_tp_sl_for_position(self, symbol: str, qty: float, entry: float) -> tuple[float | None, float | None]:
        if qty == 0 or entry == 0:
            return None, None
        
        try:
            orders = await self.client.futures_coin_get_open_orders(symbol=symbol)
            if not orders:
                return None, None
            
            sl_candidates = []
            tp_candidates = []

            for o in orders:
                # v1 로직 그대로 
                side = o.get("side")
                reduce_only = str(o.get("reduceOnly")).lower() == "true"
                if not reduce_only: continue
                
                # 포지션 줄이는 방향
                if qty > 0 and side != "SELL": continue
                if qty < 0 and side != "BUY": continue

                order_type = (o.get("type") or "").upper()
                stop_price_str = o.get("stopPrice") or o.get("price") or "0"
                try:
                    price = float(stop_price_str)
                except:
                    continue
                if price == 0.0: continue

                is_stop = order_type in {"STOP", "STOP_MARKET", "STOP_LOSS", "STOP_LOSS_LIMIT"}
                is_take = order_type in {"TAKE_PROFIT", "TAKE_PROFIT_MARKET", "TAKE_PROFIT_LIMIT"}

                if is_stop:
                    sl_candidates.append(price)
                elif is_take:
                    tp_candidates.append(price)

            sl = min(sl_candidates) if sl_candidates else None
            tp = max(tp_candidates) if tp_candidates else None
            return sl, tp
        except Exception as e:
            logging.error(f"[{symbol}] TP/SL 조회 실패: {e}")
            return None, None

    async def get_position_snapshot_stable(self, symbol: str) -> Dict:
        # v1: retry for stability
        last = await self.get_position_snapshot(symbol)
        for _ in range(3):
            await asyncio.sleep(0.2)
            cur = await self.get_position_snapshot(symbol)
            # 수량이 같으면 안정된 것으로 간주 (단순화)
            if cur["qty"] == last["qty"]:
                # 안정되면 TP/SL 조회
                sl, tp = await self.get_tp_sl_for_position(symbol, cur["qty"], cur["entry"])
                cur["sl"] = sl
                cur["tp"] = tp
                return cur
            last = cur
        
        # 마지막 시도
        sl, tp = await self.get_tp_sl_for_position(symbol, last["qty"], last["entry"])
        last["sl"] = sl
        last["tp"] = tp
        return last

    async def process_queue(self):
        logging.info("이벤트 처리 큐 루프 시작")
        while not self._stop_event.is_set():
            try:
                # 1초 타임아웃으로 wait하여 stop check
                payload = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            
            try:
                await self._process_trade_event(payload)
            except Exception as e:
                logging.error(f"이벤트 처리 중 오류: {e}")
            finally:
                self._queue.task_done()

    async def _process_trade_event(self, payload: dict):
        symbol = payload["symbol"]
        last_qty = payload["last_qty"]
        side = payload["side"]
        price = payload["price"]
        event_ts = payload["event_ts"]
        
        # 중복 체크
        last_tid = int(self._last_trade_id.get(symbol, 0))
        trade_id_int = int(payload.get("trade_id") or 0)
        
        if trade_id_int and trade_id_int <= last_tid:
            return

        # 심볼 등록
        self._seen_symbols.add(symbol)
        
        # 포지션 스냅샷 (약간의 딜레이 후)
        await asyncio.sleep(0.5)
        snap = await self.get_position_snapshot_stable(symbol)
        
        # 데이터 구성
        ts = datetime.fromtimestamp(event_ts / 1000.0, timezone.utc)
        ts_kst = ts.astimezone().strftime("%Y-%m-%d %H:%M:%S")

        # 손익비(R) 계산 (v1 로직)
        r_multiple = None
        try:
            pos_after = snap["qty"]
            signed_delta = last_qty if side == "매수" else -last_qty
            pos_before = pos_after - signed_delta
            entry_price = snap["entry"]
            stop_price = snap["sl"]
            
            if pos_before != 0 and stop_price and entry_price not in (0.0, stop_price):
                if abs(pos_after) < abs(pos_before):
                    if pos_before > 0:
                        risk = entry_price - stop_price
                        if risk != 0: r_multiple = (price - entry_price) / risk
                    elif pos_before < 0:
                        risk = stop_price - entry_price
                        if risk != 0: r_multiple = (entry_price - price) / risk
        except:
            pass
        
        # 마진 계산 등 복잡한 부분은 스냅샷 의존
        margin_val = 0.0
        # ... (v1의 마진 계산 로직 간소화 적용)
        # 필요한 경우 추가 구현. 여기서는 스냅샷의 isolated_margin 우선 사용
        
        row = {
            "시간(KST)": ts_kst,
            "심볼": symbol,
            "포지션방향": "LONG" if snap["qty"] > 0 else ("SHORT" if snap["qty"] < 0 else ""),
            "매수/매도": side,
            "수량": last_qty,
            "가격": price,
            "실현손익": payload["realized_pnl"],
            "수수료": payload["fee"],
            "수수료자산": payload["fee_asset"],
            "포지션수량": snap["qty"],
            "평균진입가": snap["entry"],
            "레버리지": snap["lev"],
            "마진타입": snap["margin_type"],
            "마진자산": snap["margin_asset"],
            "포지션마진": snap["isolated_margin"], # 간소화
            "미실현손익": snap["upnl"],
            "손절가(USD)": snap["sl"],
            "익절가(USD)": snap["tp"],
            "손익비(R)": r_multiple,
            "order_id": payload["order_id"],
            "trade_id": trade_id_int,
        }
        
        # 파일 쓰기 (Blocking I/O in executor)
        await asyncio.get_running_loop().run_in_executor(
            self._file_executor,
            self._append_row,
            row
        )

        # 구글 시트 즉시 동기화 실행 (신규 추가)
        try:
            logging.info(f"[{symbol}] 구글 시트 동기화 트리거 시작...")
            # 작업 디렉토리(/home/jeong-kihun/.openclaw)에서 sync_all_to_sheets.py 실행
            sync_proc = await asyncio.create_subprocess_exec(
                sys.executable, "/home/jeong-kihun/.openclaw/workspace/sync_all_to_sheets.py",
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            s_out, s_err = await sync_proc.communicate()
            if sync_proc.returncode == 0:
                logging.info(f"[{symbol}] 구글 시트 동기화 성공")
            else:
                logging.error(f"[{symbol}] 구글 시트 동기화 실패: {s_err.decode()}")
        except Exception as e:
            logging.error(f"구글 시트 동기화 트리거 오류: {e}")

        # 상태 업데이트
        if trade_id_int:
            self._last_trade_id[symbol] = trade_id_int
        self._last_event_ts[symbol] = int(event_ts)
        self._save_state()
        
        logging.info(f"[{symbol}] 체결 기록: {side} {last_qty} @ {price}")

    def _append_row(self, row):
        df = pd.DataFrame([row], columns=CSV_COLUMNS)
        df.to_csv(self.log_file, mode="a", index=False, header=False, encoding="utf-8-sig")
        # 리포트 생성 트리거
        self._report_trigger.schedule(self._loop)

    async def backfill_loop(self):
        logging.info("백필 루프 시작")
        while not self._stop_event.is_set():
            try:
                # 1. 새로운 활성 심볼 발견 (WS 누락 대비)
                await self._discover_active_symbols()
                
                # 2. 백필 수행
                await self._backfill_missing_trades()
            except Exception as e:
                logging.error(f"백필/심볼감지 루프 오류: {e}")

            await asyncio.sleep(BACKFILL_INTERVAL)

    async def _discover_active_symbols(self):
        """
        포지션 정보를 조회하여, 현재 포지션이 있는 심볼은 _seen_symbols에 추가한다.
        (WS가 끊긴 상태에서 새로운 심볼을 거래했을 때, backfill 대상에 포함시키기 위함)
        """
        try:
            # 타임아웃/재시도 적용
            positions = []
            for _ in range(3):
                try:
                    positions = await self.client.futures_coin_position_information()
                    break
                except Exception:
                    await asyncio.sleep(1)
            
            if not positions:
                return

            new_found = 0
            for p in positions:
                amt = float(p.get("positionAmt", 0.0))
                sym = p.get("symbol")
                if amt != 0 and sym and sym not in self._seen_symbols:
                    self._seen_symbols.add(sym)
                    new_found += 1
            
            if new_found > 0:
                logging.info(f"[Discovery] 새로운 활성 심볼 {new_found}개 발견 -> 백필 대상 추가")

        except Exception as e:
            logging.warning(f"[Discovery] 활성 심볼 조회 실패: {e}")

    async def _backfill_missing_trades(self):
        if not self._seen_symbols:
            return
        
        for symbol in list(self._seen_symbols):
            try:
                start_ts = self._last_event_ts.get(symbol)
                params = {"symbol": symbol, "limit": 1000}
                if start_ts:
                    params["startTime"] = int(start_ts) + 1
                
                if start_ts:
                    params["startTime"] = int(start_ts) + 1
                
                # Retry Logic for Network Stability
                # "Remote end closed connection" 등 일시적 네트워크 오류 방어
                trades = []
                for attempt in range(3):
                    try:
                        trades = await self.client.futures_coin_account_trades(**params)
                        break
                    except Exception as e:
                        # 재시도 가능한 에러인지 확인 (여기선 모든 에러에 대해 짧게 재시도)
                        if attempt < 2:
                            await asyncio.sleep(1)
                            continue
                        raise e

                if not trades: continue
                
                trades_sorted = sorted(trades, key=lambda x: int(x.get("time", 0)))
                
                count = 0
                for t in trades_sorted:
                    tid = int(t.get("id"))
                    ts_ms = int(t.get("time"))
                    if tid <= int(self._last_trade_id.get(symbol, 0)):
                        continue
                        
                    # 큐에 넣어서 처리 (스냅샷은 현재 시점 기준이 되겠지만, 백필 한계상 어쩔 수 없음)
                    payload = {
                        "symbol": symbol,
                        "last_qty": float(t.get("qty")),
                        "side": "매수" if t.get("side") == "BUY" else "매도",
                        "price": float(t.get("price")),
                        "realized_pnl": float(t.get("realizedPnl")),
                        "fee": float(t.get("commission")),
                        "fee_asset": t.get("commissionAsset"),
                        "order_id": t.get("orderId"),
                        "trade_id": tid,
                        "event_ts": ts_ms,
                    }
                    await self._queue.put(payload)
                    count += 1
                
                if count > 0:
                    logging.info(f"[BACKFILL] {symbol}: {count}건 복구 요청")
                    
                    # Pagination: 1000개를 꽉 채워 가져왔다면 더 있을 수 있음
                    if len(trades) >= 1000:
                        # 마지막 체결의 time을 start_ts로 갱신하여 while 루프 돌게 하거나
                        # 여기서 재귀/반복 호출.
                        # 간단히 while 루프로 처리
                        last_t = trades_sorted[-1]
                        next_start = int(last_t.get("time")) + 1
                        # 너무 루프 돌지 않게 안전장치? 여기서 재귀 호출은 stack 위험하니
                        # 내부 루프를 하나 더 만들어서 처리하는 게 나음.
                        # 하지만 구조상 _backfill_missing_trades 함수 자체를 
                        # 한 심볼씩 다 처리하도록 수정하는 게 깔끔.
                        
                        # (단순화를 위해 이번 턴엔 그냥 나가고, 다음 BACKFILL_INTERVAL(또는 즉시)에 
                        #  updated last_event_ts로 다시 긁겠지만, 
                        #  Gap이 크면 따라잡는데 오래 걸림. -> 루프 필요)
                        
                        # 루프 구현:
                        while True:
                            params["startTime"] = next_start
                            
                            # Pagination Retry Logic
                            more_trades = []
                            for attempt in range(3):
                                try:
                                    more_trades = await self.client.futures_coin_account_trades(**params)
                                    break
                                except Exception as e:
                                    if attempt < 2:
                                        await asyncio.sleep(1)
                                        continue
                                    logging.warning(f"[BACKFILL-More] Pagination fetch failed: {e}")
                                    more_trades = []
                                    break
                            
                            if not more_trades:
                                break
                            
                            more_sorted = sorted(more_trades, key=lambda x: int(x.get("time", 0)))
                            sub_count = 0
                            for t in more_sorted:
                                tid = int(t.get("id"))
                                ts_ms = int(t.get("time"))
                                if tid <= int(self._last_trade_id.get(symbol, 0)):
                                    continue
                                
                                payload = {
                                    "symbol": symbol,
                                    "last_qty": float(t.get("qty")),
                                    "side": "매수" if t.get("side") == "BUY" else "매도",
                                    "price": float(t.get("price")),
                                    "realized_pnl": float(t.get("realizedPnl")),
                                    "fee": float(t.get("commission")),
                                    "fee_asset": t.get("commissionAsset"),
                                    "order_id": t.get("orderId"),
                                    "trade_id": tid,
                                    "event_ts": ts_ms,
                                }
                                await self._queue.put(payload)
                                sub_count += 1
                            
                            if sub_count > 0:
                                logging.info(f"[BACKFILL-More] {symbol}: {sub_count}건 추가 복구")
                                last_t_more = more_sorted[-1]
                                next_start = int(last_t_more.get("time")) + 1
                                if len(more_trades) < 1000:
                                    break
                            else:
                                break

            except Exception as e:
                logging.warning(f"[BACKFILL] {symbol} 오류: {e}")


# =========================================================
# 4) WebSocket Listener
# =========================================================
async def run_ws_listener(client: AsyncClient, journal: AsyncTradeJournal):
    bm = BinanceSocketManager(client)
    
    # 3. Socket 연결
    # BinanceSocketManager가 내부적으로 Listen Key 생성 및 Keepalive를 관리함
    ts = bm.coin_futures_user_socket()

    # Heartbeat Task (터미널에 생존신고)
    async def heartbeat_loop():
        while True:
            await asyncio.sleep(300) # 5분마다
            logging.info("[Heartbeat] 로거 동작 중... (WS 연결 상태 확인)")

    heartbeat_task = asyncio.create_task(heartbeat_loop())

    # 3. Socket 연결
    # user_socket은 (async context manager)
    
    logging.info("웹소켓 연결 시작...")
    async with ts as tscm:
        while True:
            msg = await tscm.recv()
            if not msg:
                break
            
            # 메시지 파싱
            if msg.get("e") == "ORDER_TRADE_UPDATE":
                o = msg.get("o", {})
                if o.get("x") == "TRADE" and float(o.get("l", 0)) > 0:
                     payload = {
                        "symbol": o.get("s"),
                        "last_qty": float(o.get("l")),
                        "side": "매수" if o.get("S") == "BUY" else "매도",
                        "price": float(o.get("L") or o.get("ap")),
                        "realized_pnl": float(o.get("rp")),
                        "fee": float(o.get("n")),
                        "fee_asset": o.get("N"),
                        "order_id": o.get("i"),
                        "trade_id": o.get("t"),
                        "event_ts": msg.get("E"),
                    }
                     await journal._queue.put(payload)

    # 종료 시
    heartbeat_task.cancel()

# =========================================================
# 5) Main Entry
# =========================================================
async def main():
    setup_logging()
    ensure_log_file()

    client = await AsyncClient.create(API_KEY, API_SECRET)
    
    journal = AsyncTradeJournal(client, LOG_FILE)
    
    # Task 실행
    # Task 실행
    consumer_task = asyncio.create_task(journal.process_queue())
    
    # 1. 시작 시 즉시 백필 수행 (Startup Backfill)
    logging.info("Startup Backfill 시작...")
    await journal._backfill_missing_trades()
    logging.info("Startup Backfill 완료")

    backfill_task = asyncio.create_task(journal.backfill_loop())
    
    try:
        await run_ws_listener(client, journal)
    except KeyboardInterrupt:
        logging.info("종료 요청")
    except Exception as e:
        logging.error(f"메인 루프 오류: {e}")
    finally:
        journal._stop_event.set()
        await client.close_connection()
        await asyncio.gather(consumer_task, backfill_task, return_exceptions=True)
        logging.info("완료")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
