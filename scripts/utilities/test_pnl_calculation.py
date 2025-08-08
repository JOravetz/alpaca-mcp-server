#!/usr/bin/env python3
"""Test script to manually calculate SOUN P&L and verify the calculation logic."""

def calculate_soun_pnl():
    """Manually calculate SOUN P&L to verify the fix."""
    
    # SOUN trades from the data (chronological order)
    trades = [
        ("buy", 394, 12.87),     # 08:20:05
        ("buy", 394, 12.87),     # 08:20:05
        ("buy", 780, 12.81),     # 08:21:57
        ("buy", 782, 12.79),     # 08:24:54
        ("sell", 2350, 12.84),   # 08:25:29 - Close long position
        ("sell", 25000, 13.93),  # 14:48:58 - Start short position
        ("sell", 25000, 14.15),  # 14:52:54 - Add to short
        ("sell", 25000, 14.21),  # 14:55:11 - Add to short
        ("buy", 75000, 13.95),   # 15:07:14 - Cover short position
        ("buy", 3594, 13.89),    # 15:08:18
        ("sell", 3594, 13.91),   # 15:09:13
        ("buy", 7204, 13.89),    # 15:11:46
        ("sell", 7112, 13.91),   # 15:12:04
        ("buy", 7293, 13.70),    # 15:12:14
        ("sell", 3631, 13.74),   # 15:12:28
        ("sell", 3579, 13.75),   # 15:12:29
        ("sell", 175, 13.75),    # 15:12:29
        ("buy", 7262, 13.78),    # 15:15:42
        ("sell", 1000, 13.83),   # 15:16:17
        ("sell", 5722, 13.84),   # 15:16:18
        ("sell", 540, 13.84),    # 15:16:19
    ]
    
    position = 0
    avg_price = 0
    total_pnl = 0
    trade_pnls = []
    
    print("SOUN P&L Calculation:")
    print("=" * 80)
    
    for side, qty, price in trades:
        old_position = position
        old_avg = avg_price
        pnl = 0
        
        if side == "buy":
            if position >= 0:  # Long or flat
                if position == 0:
                    avg_price = price
                else:
                    avg_price = ((position * avg_price) + (qty * price)) / (position + qty)
                position += qty
                action = f"Open/Add Long: {qty} @ ${price:.2f}"
            else:  # Short position
                qty_to_cover = min(qty, abs(position))
                pnl = (avg_price - price) * qty_to_cover
                position += qty
                
                if position > 0:
                    avg_price = price
                elif position == 0:
                    avg_price = 0
                    
                action = f"Cover Short: {qty_to_cover} @ ${price:.2f}, P&L: ${pnl:.2f}"
                
        else:  # sell
            if position <= 0:  # Short or flat
                if position == 0:
                    avg_price = price
                else:
                    avg_price = ((abs(position) * avg_price) + (qty * price)) / (abs(position) + qty)
                position -= qty
                action = f"Open/Add Short: {qty} @ ${price:.2f}"
            else:  # Long position
                qty_to_sell = min(qty, position)
                pnl = (price - avg_price) * qty_to_sell
                position -= qty
                
                if position < 0:
                    avg_price = price
                elif position == 0:
                    avg_price = 0
                    
                action = f"Close Long: {qty_to_sell} @ ${price:.2f}, P&L: ${pnl:.2f}"
        
        total_pnl += pnl
        if pnl != 0:
            trade_pnls.append(pnl)
            
        print(f"{side.upper():4} {qty:6} @ ${price:6.2f} | Pos: {old_position:7} -> {position:7} | "
              f"Avg: ${old_avg:6.2f} -> ${avg_price:6.2f} | {action}")
    
    print("=" * 80)
    print(f"\nIndividual P&Ls: {[f'${p:.2f}' for p in trade_pnls]}")
    print(f"Total SOUN P&L: ${total_pnl:.2f}")
    
    # Calculate the short trade P&L explicitly
    print("\n" + "=" * 80)
    print("SHORT TRADE ANALYSIS:")
    short_sell_avg = (25000 * 13.93 + 25000 * 14.15 + 25000 * 14.21) / 75000
    short_cover = 13.95
    short_pnl = (short_sell_avg - short_cover) * 75000
    print(f"Sold 75,000 shares at average: ${short_sell_avg:.4f}")
    print(f"Bought back 75,000 shares at: ${short_cover:.2f}")
    print(f"Short trade P&L: ${short_pnl:.2f}")
    
    return total_pnl

if __name__ == "__main__":
    calculated_pnl = calculate_soun_pnl()
    print(f"\nFinal calculated SOUN P&L: ${calculated_pnl:.2f}")