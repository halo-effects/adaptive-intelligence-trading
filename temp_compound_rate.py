import math

starting_capital = 50000
current_equity = 58473
days_running = 21  # since March 3

# Compound daily rate: equity = capital * (1 + r)^days
# r = (equity/capital)^(1/days) - 1
r = (current_equity / starting_capital) ** (1 / days_running) - 1
print(f'Compound daily rate: {r*100:.4f}%')

# Annual projection
annual = starting_capital * (1 + r) ** 365
print(f'Annual projection (compound): ${annual:,.0f}')
print(f'Annual return: {((annual/starting_capital)-1)*100:.1f}%')

# For comparison: simple daily rate
simple_daily = ((current_equity - starting_capital) / starting_capital) / days_running
print(f'\nSimple daily rate: {simple_daily*100:.4f}%')
simple_annual = starting_capital * (1 + simple_daily) ** 365
print(f'Annual projection (simple compounded): ${simple_annual:,.0f}')
