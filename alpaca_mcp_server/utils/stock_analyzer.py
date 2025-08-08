import argparse
import json
import os
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import requests  # type: ignore[import-untyped]

API_KEY_ID = os.environ["APCA_API_KEY_ID"]
SECRET_KEY_ID = os.environ["APCA_API_SECRET_KEY"]


def is_premarket(current_time: datetime) -> bool:
    premarket_start = time(4, 0)  # 4:00 AM
    market_open = time(9, 30)  # 9:30 AM
    return premarket_start <= current_time.time() < market_open


def load_previous_results() -> dict[str, Any]:
    if not os.path.exists("previous_results.json"):
        try:
            with open("previous_results.json", "w") as f:
                json.dump({}, f)
        except (OSError, json.JSONDecodeError, PermissionError):
            return {}
    try:
        with open("previous_results.json") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, PermissionError):
        return {}


def save_current_results(results: list[dict[str, Any]]) -> None:
    results_dict = {
        result["symbol"]: {
            "gradient_recent": result["gradient_recent"],
            "volume": result["volume"],
            "trades": result["trades"],
        }
        for result in results
    }
    with open("previous_results.json", "w") as f:
        json.dump(results_dict, f)


def generate_html(results: list[dict[str, Any]], timestamp: str) -> str:
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="60">
    <title>Stock Metrics {timestamp} EST</title>
    <script type="text/javascript" src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script type="text/javascript" src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.css">
    <style>
        html.loading {{
            visibility: hidden;
        }}
        body {{
            font-family: Arial, sans-serif;
            background-color: #000;
            color: #fff;
            margin: 20px;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #fff;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        table.dataTable,
        .dataTables_wrapper,
        .dataTables_wrapper tbody,
        .dataTables_wrapper tbody tr,
        .dataTables_wrapper tbody td {{
            background-color: #000 !important;
            color: #fff !important;
        }}
        .dataTables_wrapper thead th {{
            background-color: #1a1a1a !important;
            color: #fff !important;
            font-weight: bold;
            border: 1px solid #333;
            cursor: pointer;
            padding: 8px;
        }}
        .dataTables_wrapper td {{
            border: 1px solid #333;
            padding: 8px;
        }}
        .dataTables_wrapper tbody tr:hover td {{
            background-color: #1a1a1a !important;
        }}
        .dataTables_wrapper td:not(:first-child) {{
            text-align: right !important;
        }}
        a {{
            color: #4a9eff;
            text-decoration: none;
        }}
        a:hover {{
            color: #66b3ff;
            text-decoration: underline;
        }}
        .dataTables_wrapper .dataTables_length,
        .dataTables_wrapper .dataTables_filter,
        .dataTables_wrapper .dataTables_info,
        .dataTables_wrapper .dataTables_paginate {{
            color: #fff !important;
            margin: 10px 0;
        }}
        .dataTables_wrapper label {{
            color: #fff !important;
        }}
        .dataTables_wrapper .dataTables_info {{
            color: #fff !important;
            padding: 10px 0;
        }}
        .dataTables_wrapper .dataTables_paginate .paginate_button {{
            color: #fff !important;
            border: 1px solid #333;
            background-color: #1a1a1a;
            margin: 0 4px;
            padding: 5px 10px;
        }}
        .dataTables_wrapper .dataTables_paginate .paginate_button.current {{
            background-color: #2d2d2d !important;
            color: #fff !important;
            border-color: #666;
        }}
        .dataTables_wrapper .dataTables_paginate .paginate_button:hover {{
            background-color: #2d2d2d !important;
            color: #fff !important;
        }}
        .dataTables_wrapper .dataTables_length select,
        .dataTables_wrapper .dataTables_filter input {{
            background-color: #1a1a1a !important;
            color: #fff !important;
            border: 1px solid #333;
            padding: 5px;
            margin: 0 5px;
        }}
        .dataTables_wrapper .dataTables_paginate .paginate_button.disabled,
        .dataTables_wrapper .dataTables_paginate .paginate_button.disabled:hover {{
            color: #666 !important;
            background-color: #1a1a1a !important;
            cursor: default;
        }}
        .dataTables_wrapper .dataTables_length select option {{
            background-color: #1a1a1a;
            color: #fff;
        }}
        .dataTables_filter input::placeholder {{
            color: #999;
        }}
        .dataTables_wrapper tbody tr.high-trades td {{
            color: #00ff00 !important;
            font-weight: bold !important;
        }}
    </style>
    <script type="text/javascript">
        document.documentElement.className = 'loading';
    </script>
</head>
<body>
    <div class="container">
        <h1>Stock Metrics for {timestamp} EST</h1>
        <table id="stockTable" class="display">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>Close</th>
                    <th>% Change</th>
                    <th>Gradient/2</th>
                    <th>Recent</th>
                    <th>Volume</th>
                    <th>Trades</th>
                    <th>∆Gradient</th>
                    <th>∆Volume</th>
                    <th>∆Trades</th>
                </tr>
            </thead>
            <tbody>
"""
    for result in results:
        row_class = "high-trades" if result["trades"] > 1000 else ""
        html += f"""
                <tr class="{row_class}">
                    <td><a href="https://finance.yahoo.com/quote/{result["symbol"]}" target="_blank">{result["symbol"]}</a></td>
                    <td>{result["price"]:.3f}</td>
                    <td>{result["day_close"]:.3f}</td>
                    <td data-order="{result["percent"]}">{result["percent"]:.1f}%</td>
                    <td>{result["gradient_full"]:.1f}</td>
                    <td>{result["gradient_recent"]:.1f}</td>
                    <td>{result["volume"]}</td>
                    <td>{result["trades"]}</td>
                    <td>{result["gradient_change"]:.1f}</td>
                    <td>{result["volume_change"]}</td>
                    <td>{result["trades_change"]}</td>
                </tr>"""
    html += """
            </tbody>
        </table>
    </div>
    <script>
        $(document).ready(function() {
            const table = $('#stockTable').DataTable({
                "order": [[7, "desc"]],
                "pageLength": 25,
                "columnDefs": [
                    { "type": "num", "targets": [1,2,3,4,5,6,7,8,9,10] }
                ]
            });
            document.documentElement.className = '';
        });
    </script>
</body>
</html>
    """
    return html


def run(args: argparse.Namespace) -> None:
    LIST = str(args.list) if args.list else "combined"
    previous_results = load_previous_results()

    with open(LIST + ".lis") as f:
        universe = [line.strip().split()[0].upper() for line in f if line.strip()]

    url = f"https://data.alpaca.markets/v2/stocks/snapshots?symbols={','.join(universe)}"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": API_KEY_ID,
        "APCA-API-SECRET-KEY": SECRET_KEY_ID,
    }
    response = requests.get(url, headers=headers, timeout=30)
    snapshots = response.json()
    results = []

    current_est = datetime.now(ZoneInfo("America/New_York"))
    premarket = is_premarket(current_est)

    for symbol in universe:
        try:
            snapshot = snapshots.get(symbol)
            if not snapshot or "latestTrade" not in snapshot or "minuteBar" not in snapshot:
                continue

            trade_time = datetime.fromisoformat(
                snapshot["latestTrade"]["t"].replace("Z", "+00:00")
            ).astimezone(ZoneInfo("America/New_York"))
            if trade_time.date() != current_est.date():
                continue

            if int(snapshot["minuteBar"]["n"]) < 50:
                continue

            price_now = float(snapshot["latestTrade"]["p"])
            day_close = float(snapshot["dailyBar"]["c"])
            minute_volume = int(snapshot["minuteBar"]["v"])
            minute_trades = int(snapshot["minuteBar"]["n"])

            reference_price = day_close if premarket else float(snapshot["prevDailyBar"]["c"])

            percent = ((price_now - reference_price) / reference_price) * 100.0
            gradient_full = percent / 2.0
            gradient_recent = ((price_now - day_close) / day_close) * 100.0

            prev_data = previous_results.get(symbol, {})
            gradient_change = gradient_recent - prev_data.get("gradient_recent", gradient_recent)
            volume_change = minute_volume - prev_data.get("volume", minute_volume)
            trades_change = minute_trades - prev_data.get("trades", minute_trades)

            results.append(
                {
                    "symbol": symbol,
                    "price": price_now,
                    "day_close": day_close,
                    "percent": percent,
                    "gradient_full": gradient_full,
                    "gradient_recent": gradient_recent,
                    "gradient_change": gradient_change,
                    "volume": minute_volume,
                    "volume_change": volume_change,
                    "trades": minute_trades,
                    "trades_change": trades_change,
                }
            )
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
            continue

    results.sort(key=lambda x: x["trades"], reverse=True)
    timestamp = current_est.strftime("%Y-%m-%d %H:%M:%S")
    html_content = generate_html(results, timestamp)

    try:
        with open("latest.html", "w") as f:
            f.write(html_content)
        # Use subprocess instead of os.system for security
        import subprocess
        subprocess.run(
            [
                "scp", "-q", "latest.html",
                "stockminer@www.stockminer.net:/home/71/00/8200071/public_html/latest/index.html"
            ],
            check=True
        )
        print(f"Updated {timestamp}")
    except Exception as e:
        print(f"Error saving/uploading file: {str(e)}")

    save_current_results(results)


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("--list", type=str, default="", help="Symbol list (default=combined.lis)")
    ARGUMENTS = PARSER.parse_args()
    run(ARGUMENTS)
