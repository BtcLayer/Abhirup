# liquidity_bot/utils/helpers.py

def format_price(price):
    """
    Formats a price for clean display, using commas and 4 decimal places.
    """
    if price is None:
        return "N/A"
    return f"${price:,.4f}"