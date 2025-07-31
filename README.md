## 📊 Liquidity Pool Strategy Suite — Backtesting, Paper Trading & Analytics

This repository offers a complete implementation and validation of **Concentrated Liquidity with Impermanent Loss (IL) Management Techniques** under liquidity provisioning strategies. It covers **backtesting**, **paper trading**, **forward simulation**, and **data-driven analytics** to lay the groundwork for a powerful automated trading bot, especially suited for DEXs like **PancakeSwap** and **Uniswap V3**.

All dynamic liquidity ranges are calculated using a rolling **2-hour window** from historical OHLCV data (fetched using `ccxt`) to simulate near-realistic trading environments. Paper trading is integrated with **Google Sheets** via the **Google Sheets API** using `credentials1.json`.

---

### 📂 Folder Breakdown & Strategy Insights

#### ✅ 1. `ETH_USDT`&#x20;

Implements both **backtesting** and **paper trading** for the **ETH/USDT** pair on **PancakeSwap**, assuming a starting capital of **\$1,000** and a fee tier of **0.05%**.\
📌 **Deployed on server** — results actively logged to:\
📄 [Google Sheet Output](https://docs.google.com/spreadsheets/d/1_DZ6ztD5M2eUBKwPurz2Zcvvu3s8EFWsVTwV33o2zU8/edit?usp=sharing)

---

#### ✅ 2. `Strategy_validation`

Focused on **forward testing and simulation** for the **ETH/USDT** pair on **Uniswap V3**, using **on-chain data from Ethereum Mainnet**.

- Pulls data using your **Alchemy mainnet RPC URL**
- Uses Pool ID: `0x11b815efb8f581194ae79006d24e0d814b7697f6` to capture accurate fee generation behavior from the correct smart contract
- `config.py` holds environment-specific config
- `simulation_engine.py` performs the core forward testing logic\
  📌 **Deployed on server** — real-time output logged at:\
  📄 [Uniswap Strategy Sheet](https://docs.google.com/spreadsheets/d/1cUD41LW8KyWMnp9xflX6ZR6XI2382i107p-eVw0qdPo/edit?usp=sharing)

---

#### ✅ 3. `WBNB_USDT` 

Handles backtesting and paper trading for the **WBNB/USDT** pair on **PancakeSwap** using similar dynamic range calculation and IL management techniques.\
📌 **Deployed on server** — outputs recorded in:\
📄 [WBNB\_USDT Pancake Sheet](https://docs.google.com/spreadsheets/d/11GjL8s7mS_AfAdrFyj6ogV5SYOGeuSgGLTmij9TufmA/edit?usp=sharing)

---

### 📈 Trade Pattern Analysis & Automation Utilities

These scripts support data analysis to identify edge-generating patterns from historical or live trading behavior — an essential step toward intelligent bot automation.

#### ✅ 4. `Clustering_entire_data`

Applies **MiniBatch K-Means Clustering** on the entire dataset to identify clusters of similar trades and behavior patterns.\
📌 **Deployed on server**

---

#### ✅ 5. `clustering_top`

Provides **deeper analysis** of successful trades and identifies key patterns and analogies. Also helps discover **reverse trade opportunities** by analyzing abnormal deviations.\
📌 **Deployed on server**

---

#### ✅ 6. `dataFetchingfromArkham`

An advanced data ingestion pipeline using **Arkham Intelligence API** to fetch:

- Transfers
- Swaps
- Inflows & Outflows
- Balances

for selected wallet addresses.

The script writes data to a Google Sheet and refreshes every **4 minutes**, appending newly encountered transactions.\
⚠️ **Currently tested with only 2 addresses**, but built to scale.\
📄 [Arkham API Output Sheet](https://docs.google.com/spreadsheets/d/1c04Mf3QpGDa0TunD6El9othMyjccc8hOcLrWaaJUdyM/edit?usp=sharing)\
📌 *Not yet deployed*

---

#### ✅ 7. `drawdown.py`

Visualizes **Maximum Drawdown (MDD)** curves over time to assess capital risk and exposure per strategy or trader.\
📌 **Deployed on server**

---

#### ✅ 8. `plot.py`

Generates:

- **Equity Curves**
- **Asset Allocation Charts**
- **Combined MDD overlays**

These plots provide rich, graphical insights into the behavior and risk profile of top-performing addresses.\
📌 **Deployed on server**

---

### 🚀 Final Goal

To build an **automated trading bot** that:

- Adapts to market dynamics using **concentrated liquidity & volatility-based ranges**
- Tracks performance through **real-time paper trading in Google Sheets**
- Identifies **profitable trade patterns using clustering & analytics**
- Leverages **live on-chain data & API integrations**

This project unifies simulation, visualization, and data-driven decision-making into a cohesive framework for advanced crypto strategy development.
