#!/usr/bin/env python3
"""Verify total P&L calculation matches account statement."""

# From the MCP tool (old calculation)
mcp_reported = {
    "SOUN": 994.16,
    "PAPL": 1326.04,
    "MRM": 1090.59,
    "CLIK": 151.51
}

# Corrected SOUN calculation
corrected_soun = 11994.16

# Calculate corrected total
corrected_total = corrected_soun + mcp_reported["PAPL"] + mcp_reported["MRM"] + mcp_reported["CLIK"]

print("P&L Analysis:")
print("=" * 50)
print("\nMCP Tool Reported:")
for symbol, pnl in mcp_reported.items():
    print(f"  {symbol:6} ${pnl:>10,.2f}")
print(f"  {'Total':6} ${sum(mcp_reported.values()):>10,.2f}")

print("\nCorrected Calculation:")
print(f"  {'SOUN':6} ${corrected_soun:>10,.2f} (was ${mcp_reported['SOUN']:.2f})")
print(f"  {'PAPL':6} ${mcp_reported['PAPL']:>10,.2f}")
print(f"  {'MRM':6} ${mcp_reported['MRM']:>10,.2f}")
print(f"  {'CLIK':6} ${mcp_reported['CLIK']:>10,.2f}")
print(f"  {'Total':6} ${corrected_total:>10,.2f}")

print("\nAccount Statement Shows: $14,562.30")
print(f"Corrected Calculation:    ${corrected_total:,.2f}")
print(f"Difference:               ${14562.30 - corrected_total:,.2f}")