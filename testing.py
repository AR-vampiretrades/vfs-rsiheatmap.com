from flask import Flask, render_template
import requests
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from flask import Flask, jsonify
from flask_cors import CORS
from flask_frozen import Freezer
import threading    

# Disable interactive mode initially (graph won't show until data is loaded)
plt.ion()

# === Flask Setup ===

app = Flask(__name__)
freezer = Freezer(app)
app = Flask(__name__, template_folder=r'E:\Ahsan Others\New Softwares\template')
CORS(app)
# Email sending function
def send_email(subject, body, to_email):
    from_email = "vfsanalytics@gmail.com"   
    password = "@VFSAnalytics01"
    smtp_server = "smtp.example.com"
    smtp_port = 587

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

# RSI Calculation
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    for i in range(window, len(data)):  
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (window - 1) + gain.iloc[i]) / window
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (window - 1) + loss.iloc[i]) / window
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Data fetch with retry mechanism
def fetch_data(symbol, granularity="15m", product_type="USDT-FUTURES"):
    url = "https://api.bitget.com/api/v2/mix/market/candles"
    params = {
        "symbol": symbol,
        "granularity": granularity,
        "productType": product_type
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    while True:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()['data']
            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"])
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
            df['close'] = pd.to_numeric(df['close'])
            df.set_index('timestamp', inplace=True)
            df['rsi'] = calculate_rsi(df['close'])
            return df
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {e} — Retrying in 60 seconds")
            time.sleep(60)

# Crypto pairs
pairs = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "ADAUSDT",
         "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]

# === Email Alert Mechanism ===
def check_rsi_and_send_email():
    for pair in pairs:
        print(f"📊 Checking RSI for {pair}...")
        df = fetch_data(pair)
        if df is not None:
            rsi = df['rsi'].iloc[-1]
            if rsi > 70:
                send_email(f"RSI Overbought Alert for {pair}", f"{pair} has crossed the overbought threshold! RSI={rsi}", "user@example.com")
            elif rsi < 30:
                send_email(f"RSI Oversold Alert for {pair}", f"{pair} has crossed the oversold threshold! RSI={rsi}", "user@example.com")

# === Auto-refresh loop ===
def plot_rsi_graph():
    plt.ion()  # Interactive mode for live updates

    while True:
        now = datetime.utcnow()
        seconds_to_next_cycle = 180 - (now.minute % 3) * 60 - now.second
        print(f"⏳ Waiting {seconds_to_next_cycle}s to sync with 3-minute interval...")
        time.sleep(seconds_to_next_cycle)

        print(f"\n🔄 Updating RSI chart at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Fetch all data
        all_data = {}
        for pair in pairs:
            print(f"📊 Fetching data for {pair}...")
            df = fetch_data(pair)
            if df is not None:
                all_data[pair] = df
            time.sleep(0.1)

        # Get RSI values
        rsi_values = {pair: df['rsi'].iloc[-1] for pair, df in all_data.items() if not df['rsi'].isna().all()}
        rsi_df = pd.DataFrame(list(rsi_values.items()), columns=["Pair", "RSI"])

        # Plotting graph
        plt.clf()  # Clear the figure for each new refresh
        fig, ax = plt.subplots(figsize=(14, 6))

        # Plot RSI Zones
        ax.axhline(70, color='red', linestyle='--', linewidth=1)
        ax.axhline(50, color='gray', linestyle='--', linewidth=1)
        ax.axhline(30, color='green', linestyle='--', linewidth=1)

        ax.text(101, 70, 'Overbought (70)', color='red', va='center')
        ax.text(101, 50, 'Neutral (50)', color='gray', va='center')
        ax.text(101, 30, 'Oversold (30)', color='green', va='center')

        for _, row in rsi_df.iterrows():
            ax.plot(row['RSI'], row['RSI'], 'o', color='blue')
            ax.text(row['RSI'], row['RSI'], row['Pair'], ha='center', va='bottom', fontsize=9)

        ax.set_xlim(20, 100)
        ax.set_ylim(20, 100)
        ax.set_xlabel("RSI Value")
        ax.set_ylabel("RSI Level")
        ax.set_title("RSI Chart - Bitget Futures (15m Interval) | Auto-refresh every 3 minutes")
        ax.grid(True, linestyle='--', alpha=0.5)

        plt.tight_layout()
        plt.show()  # Show the plot in the main thread (important!)

        print("\n⏳ Refreshing in 3 minutes...")
        plt.pause(120)  # Pause for 3 minutes before next update

def plot_rsi_graph_forever():
    plt.ion()
    while True:
        now = datetime.utcnow()
        seconds_to_next_cycle = 180 - (now.minute % 3) * 60 - now.second
        print(f"\n⏳ Waiting {seconds_to_next_cycle}s to sync with 3-minute interval...")
        time.sleep(seconds_to_next_cycle)

        print(f"\n🔄 Updating RSI chart at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

        all_data = {}
        for pair in pairs:
            print(f"📊 Fetching data for {pair}...")
            df = fetch_data(pair)
            if df is not None:
                all_data[pair] = df
            time.sleep(0.1)

        # Extract RSI and plot
        rsi_values = {pair: df['rsi'].iloc[-1] for pair, df in all_data.items() if not df['rsi'].isna().all()}
        rsi_df = pd.DataFrame(list(rsi_values.items()), columns=["Pair", "RSI"])

        plt.clf()
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.axhline(70, color='red', linestyle='--', linewidth=1)
        ax.axhline(50, color='gray', linestyle='--', linewidth=1)
        ax.axhline(30, color='green', linestyle='--', linewidth=1)
        ax.set_xlim(20, 100)
        ax.set_ylim(20, 100)

        for _, row in rsi_df.iterrows():
            ax.plot(row['RSI'], row['RSI'], 'o', color='blue')
            ax.text(row['RSI'], row['RSI'], row['Pair'], ha='center', va='bottom', fontsize=9)

        ax.set_xlabel("RSI Value")
        ax.set_ylabel("RSI Level")
        ax.set_title("RSI Chart - Bitget Futures (15m Interval) | Auto-refresh every 3 minutes")
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.draw()
        plt.pause(120)  # Wait 3 minutes before loop restarts

# === Flask Route to Trigger RSI Recalculation ===
@app.route('/refresh', methods=['GET'])
def refresh_data():
    print("🔄 Refreshing RSI data...")
    check_rsi_and_send_email()  # Recalculate RSI and send email alerts
    return jsonify({"message": "RSI data refreshed and emails sent!"})

# Add this route to serve the index.html page
@app.route('/')
def index():
    return render_template('index.html')

# Add this route to serve the current RSI data in JSON format
@app.route('/rsi-values', methods=['GET'])
def rsi_values():
    all_data = {}
    for pair in pairs:
        print(f"📊 Fetching data for {pair}...")
        df = fetch_data(pair)
        if df is not None:
            all_data[pair] = df['rsi'].iloc[-1]
        time.sleep(0.1)

    return jsonify(all_data)

# Function to run Flask app in a separate thread
def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Flask app thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # RSI plotting thread (infinite loop)
    rsi_thread = threading.Thread(target=plot_rsi_graph_forever)
    rsi_thread.daemon = True
    rsi_thread.start()

    # Keep main thread alive
    while True:
        time.sleep(60)
