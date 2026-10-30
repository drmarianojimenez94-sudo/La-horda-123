"""Research-only isolated-margin long futures model. Never places orders."""
from dataclasses import dataclass

@dataclass(frozen=True)
class FuturesCosts:
    taker_fee: float = .0005
    slippage: float = .0005
    funding_per_8h: float = .0001
    maintenance_margin: float = .005

def eligible(win_rate, sample_count, reward_risk, expected_net, liquid, trend, leverage=2.):
    return (win_rate is not None and sample_count >= 100 and win_rate > .65
            and reward_risk >= 3 and expected_net > 0 and liquid and trend
            and 1 < leverage <= 2)

def simulate_isolated_long(entry, exit_price, collateral, leverage, hours, costs=FuturesCosts(),
                           lowest_price=None):
    """Conservative scenario estimate, not an exchange-accurate liquidation engine.
    Funding charged at each started 8-hour interval. No live trading.
    """
    import math
    if min(entry, exit_price, collateral) <= 0 or not 1 <= leverage <= 2 or hours < 0:
        raise ValueError("Invalid futures inputs")
    notional=collateral*leverage
    qty=notional/entry
    open_fee=notional*(costs.taker_fee+costs.slippage)
    funding=math.ceil(hours/8)*notional*costs.funding_per_8h
    # Simplified isolated long liquidation threshold: equity <= maintenance + closing fees.
    maintenance=notional*costs.maintenance_margin
    closing_reserve=notional*(costs.taker_fee+costs.slippage)
    liquidation_price=entry-(collateral-open_fee-funding-maintenance-closing_reserve)/qty
    breached=lowest_price is not None and lowest_price <= liquidation_price
    if breached:
        return dict(liquidated=True, liquidation_price=liquidation_price,
                    final_collateral=0., pnl=-collateral,
                    warning="Conservative full collateral loss; intrabar path unknown")
    closing_notional=qty*exit_price
    close_fee=closing_notional*(costs.taker_fee+costs.slippage)
    pnl=qty*(exit_price-entry)-open_fee-close_fee-funding
    return dict(liquidated=False, liquidation_price=liquidation_price,
                final_collateral=max(0.,collateral+pnl), pnl=pnl,
                funding=funding, fees=open_fee+close_fee)
