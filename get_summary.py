import sys
import os
import json

# Add current directory to path
sys.path.append(os.getcwd())

from bot_modules import PerformanceTracker

def main():
    log_path = 'Binance_Signal_Predictor/logs/trading_log.jsonl'
    tracker = PerformanceTracker(log_path)
    summary = tracker.get_performance_summary()
    
    if summary:
        print(json.dumps(summary, indent=2))
    else:
        print("No summary available.")

if __name__ == "__main__":
    main()
