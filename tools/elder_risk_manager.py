"""
Alexander Elder's Risk Management System
Based on "Trading for a Living" - Chapter on Money Management

Key principles:
1. 6% Rule: Stop trading for the month if down 6% from month's starting equity
2. 2% Rule: Risk no more than 2% of equity on any single trade
3. Position Sizing: Based on stop-loss distance and account risk
4. Maximum positions: Never risk more than 6% total across all positions
"""

import json
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


class ElderRiskManager:
    """
    Elder's Risk Management System
    
    The 6% Rule (Monthly Drawdown Brake):
    - Track month's starting equity
    - If current equity drops 6% from month start → STOP TRADING
    - Resume next month with fresh start
    - Protects you from catastrophic losses during bad months
    
    The 2% Rule (Per-Trade Risk):
    - Never risk more than 2% of equity on a single trade
    - Position size = (Account Risk × Account Equity) / (Entry - Stop)
    - Example: $100k account, 2% risk, $5 stop → 400 shares max
    
    The 6% Total Rule (Portfolio Risk):
    - Sum of all position risks ≤ 6% of equity
    - Example: 3 positions × 2% each = 6% max
    - Prevents over-leveraging
    """
    
    def __init__(self, data_dir: str = "./data"):
        """
        Initialize Risk Manager
        
        Args:
            data_dir: Directory for storing risk management data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.risk_file = self.data_dir / "risk_management.json"
        
        # Risk parameters (Elder's recommendations)
        self.monthly_drawdown_limit = 0.06  # 6% monthly drawdown brake
        self.per_trade_risk_limit = 0.02    # 2% max risk per trade
        self.total_portfolio_risk = 0.06    # 6% total portfolio risk
        self.max_daily_loss = 0.02          # 2% daily loss limit (my addition)
        
        # Load or initialize risk data
        self.risk_data = self._load_risk_data()
    
    def _load_risk_data(self) -> Dict[str, Any]:
        """Load risk management data from file"""
        if self.risk_file.exists():
            with open(self.risk_file, 'r') as f:
                return json.load(f)
        else:
            return self._initialize_risk_data()
    
    def _initialize_risk_data(self) -> Dict[str, Any]:
        """Initialize risk management data structure"""
        today = date.today()
        return {
            "current_month": today.strftime("%Y-%m"),
            "month_start_equity": 0.0,
            "month_start_date": today.strftime("%Y-%m-%d"),
            "current_equity": 0.0,
            "month_high_equity": 0.0,
            "month_low_equity": 0.0,
            "trading_suspended": False,
            "suspension_reason": None,
            "trades_this_month": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "consecutive_losses": 0,
            "max_consecutive_losses": 0,
            "daily_equity_start": 0.0,
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_risk_data(self):
        """Save risk management data to file"""
        self.risk_data["last_updated"] = datetime.now().isoformat()
        with open(self.risk_file, 'w') as f:
            json.dump(self.risk_data, f, indent=2)
    
    def start_new_month(self, starting_equity: float):
        """
        Start new month - reset drawdown tracking
        
        Args:
            starting_equity: Account equity at start of month
        """
        today = date.today()
        current_month = today.strftime("%Y-%m")
        
        # Check if new month
        if current_month != self.risk_data.get("current_month"):
            print(f"\n{'='*80}")
            print(f"📅 NEW MONTH STARTED: {current_month}")
            print(f"{'='*80}")
            
            # Archive previous month's stats
            prev_month = self.risk_data.get("current_month")
            if prev_month:
                print(f"\n📊 PREVIOUS MONTH SUMMARY ({prev_month}):")
                print(f"   Starting Equity: ${self.risk_data.get('month_start_equity', 0):,.2f}")
                print(f"   Ending Equity: ${self.risk_data.get('current_equity', 0):,.2f}")
                print(f"   Total P&L: ${self.risk_data.get('total_profit_loss', 0):,.2f}")
                print(f"   Trades: {self.risk_data.get('trades_this_month', 0)}")
                print(f"   Win Rate: {self._calculate_win_rate():.1f}%")
                print(f"   Max Drawdown: {self._calculate_max_drawdown():.2f}%")
                if self.risk_data.get("trading_suspended"):
                    print(f"   ⚠️  Trading was suspended: {self.risk_data.get('suspension_reason')}")
            
            # Reset for new month
            self.risk_data = {
                "current_month": current_month,
                "month_start_equity": starting_equity,
                "month_start_date": today.strftime("%Y-%m-%d"),
                "current_equity": starting_equity,
                "month_high_equity": starting_equity,
                "month_low_equity": starting_equity,
                "trading_suspended": False,
                "suspension_reason": None,
                "trades_this_month": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_profit_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "consecutive_losses": 0,
                "max_consecutive_losses": 0,
                "daily_equity_start": starting_equity,
                "last_updated": datetime.now().isoformat()
            }
            
            print(f"\n✅ Month reset - Starting equity: ${starting_equity:,.2f}")
            print(f"🛡️  Trading enabled - 6% drawdown limit: ${starting_equity * 0.06:,.2f}")
            print(f"{'='*80}\n")
            
            self._save_risk_data()
    
    def update_equity(self, current_equity: float) -> Tuple[bool, str]:
        """
        Update current equity and check for 6% drawdown rule
        
        Args:
            current_equity: Current account equity
            
        Returns:
            Tuple of (can_trade, message)
        """
        # Start new month if needed
        self.start_new_month(current_equity)
        
        # Update equity
        self.risk_data["current_equity"] = current_equity
        
        # Update month high/low
        if current_equity > self.risk_data["month_high_equity"]:
            self.risk_data["month_high_equity"] = current_equity
        if current_equity < self.risk_data["month_low_equity"]:
            self.risk_data["month_low_equity"] = current_equity
        
        # Calculate drawdown from month start
        month_start = self.risk_data["month_start_equity"]
        if month_start > 0:
            drawdown = (month_start - current_equity) / month_start
        else:
            drawdown = 0.0
        
        # Check 6% monthly drawdown rule
        if drawdown >= self.monthly_drawdown_limit and not self.risk_data["trading_suspended"]:
            self.risk_data["trading_suspended"] = True
            self.risk_data["suspension_reason"] = (
                f"6% monthly drawdown limit reached. "
                f"Started: ${month_start:,.2f}, Current: ${current_equity:,.2f}, "
                f"Loss: ${month_start - current_equity:,.2f} ({drawdown*100:.2f}%)"
            )
            self._save_risk_data()
            
            return False, (
                f"\n{'='*80}\n"
                f"🚨 TRADING SUSPENDED - 6% MONTHLY DRAWDOWN LIMIT REACHED\n"
                f"{'='*80}\n"
                f"Month Start: ${month_start:,.2f}\n"
                f"Current Equity: ${current_equity:,.2f}\n"
                f"Loss: ${month_start - current_equity:,.2f} ({drawdown*100:.2f}%)\n"
                f"\n"
                f"⛔ NO TRADING ALLOWED until next month\n"
                f"📚 Elder's 6% Rule: Protects you from catastrophic losses\n"
                f"💡 Use this time to:\n"
                f"   1. Review all trades this month\n"
                f"   2. Identify what went wrong\n"
                f"   3. Improve your trading plan\n"
                f"   4. Come back stronger next month\n"
                f"{'='*80}\n"
            )
        
        # Check if trading is suspended
        if self.risk_data["trading_suspended"]:
            return False, (
                f"⛔ TRADING SUSPENDED: {self.risk_data['suspension_reason']}\n"
                f"Resume trading next month."
            )
        
        # Check daily loss limit (2%)
        daily_start = self.risk_data.get("daily_equity_start", current_equity)
        if daily_start > 0:
            daily_loss = (daily_start - current_equity) / daily_start
            if daily_loss >= self.max_daily_loss:
                return False, (
                    f"⚠️  DAILY LOSS LIMIT REACHED ({daily_loss*100:.2f}%)\n"
                    f"Daily Start: ${daily_start:,.2f}\n"
                    f"Current: ${current_equity:,.2f}\n"
                    f"Stop trading for today. Resume tomorrow."
                )
        
        self._save_risk_data()
        return True, f"✅ Trading allowed - Drawdown: {drawdown*100:.2f}%"
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_price: float,
        current_equity: float,
        risk_percent: float = 0.02
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate position size using Elder's 2% rule
        
        Formula: Position Size = (Account Risk × Equity) / Risk Per Share
        Where: Risk Per Share = |Entry Price - Stop Price|
        
        Args:
            entry_price: Intended entry price
            stop_price: Stop-loss price
            current_equity: Current account equity
            risk_percent: Risk per trade (default: 2% = 0.02)
            
        Returns:
            Tuple of (shares, details_dict)
        """
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_price)
        
        if risk_per_share == 0:
            return 0, {
                "error": "Stop price equals entry price",
                "shares": 0,
                "dollar_risk": 0
            }
        
        # Calculate position size
        dollar_risk = current_equity * risk_percent
        shares = int(dollar_risk / risk_per_share)
        
        # Ensure we don't exceed our risk limits
        actual_dollar_risk = shares * risk_per_share
        actual_risk_percent = actual_dollar_risk / current_equity if current_equity > 0 else 0
        
        return shares, {
            "shares": shares,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "risk_per_share": risk_per_share,
            "dollar_risk": actual_dollar_risk,
            "risk_percent": actual_risk_percent * 100,
            "position_value": shares * entry_price,
            "max_loss_if_stopped": actual_dollar_risk
        }
    
    def can_open_position(
        self,
        position_risk: float,
        current_open_positions_risk: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Check if new position can be opened without exceeding 6% total risk
        
        Args:
            position_risk: Risk dollar amount for new position
            current_open_positions_risk: Total risk from existing positions
            
        Returns:
            Tuple of (can_open, message)
        """
        current_equity = self.risk_data.get("current_equity", 0)
        if current_equity == 0:
            return False, "Equity not set"
        
        # Calculate total risk with new position
        total_risk = current_open_positions_risk + position_risk
        total_risk_percent = total_risk / current_equity
        
        # Check against 6% total portfolio risk
        if total_risk_percent > self.total_portfolio_risk:
            return False, (
                f"❌ Total portfolio risk would exceed 6% limit\n"
                f"Current positions risk: ${current_open_positions_risk:,.2f}\n"
                f"New position risk: ${position_risk:,.2f}\n"
                f"Total risk: ${total_risk:,.2f} ({total_risk_percent*100:.2f}%)\n"
                f"Limit: 6%"
            )
        
        return True, f"✅ Position allowed - Total risk: {total_risk_percent*100:.2f}%"
    
    def record_trade(self, profit_loss: float, trade_type: str = "day_trade"):
        """
        Record trade results
        
        Args:
            profit_loss: Profit (positive) or loss (negative) from trade
            trade_type: Type of trade (day_trade, swing, etc.)
        """
        self.risk_data["trades_this_month"] += 1
        self.risk_data["total_profit_loss"] += profit_loss
        
        # Update win/loss stats
        if profit_loss > 0:
            self.risk_data["winning_trades"] += 1
            self.risk_data["consecutive_losses"] = 0
            if profit_loss > self.risk_data.get("largest_win", 0):
                self.risk_data["largest_win"] = profit_loss
        else:
            self.risk_data["losing_trades"] += 1
            self.risk_data["consecutive_losses"] += 1
            if self.risk_data["consecutive_losses"] > self.risk_data.get("max_consecutive_losses", 0):
                self.risk_data["max_consecutive_losses"] = self.risk_data["consecutive_losses"]
            if profit_loss < self.risk_data.get("largest_loss", 0):
                self.risk_data["largest_loss"] = profit_loss
        
        self._save_risk_data()
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk management status"""
        month_start = self.risk_data.get("month_start_equity", 0)
        current = self.risk_data.get("current_equity", 0)
        
        if month_start > 0:
            drawdown = (month_start - current) / month_start
            drawdown_pct = drawdown * 100
            remaining_drawdown = (self.monthly_drawdown_limit - drawdown) * 100
        else:
            drawdown_pct = 0
            remaining_drawdown = 6.0
        
        return {
            "month": self.risk_data.get("current_month"),
            "month_start_equity": month_start,
            "current_equity": current,
            "month_pnl": self.risk_data.get("total_profit_loss", 0),
            "drawdown_percent": drawdown_pct,
            "remaining_drawdown_percent": remaining_drawdown,
            "trading_allowed": not self.risk_data.get("trading_suspended", False),
            "suspension_reason": self.risk_data.get("suspension_reason"),
            "trades_count": self.risk_data.get("trades_this_month", 0),
            "win_rate": self._calculate_win_rate(),
            "consecutive_losses": self.risk_data.get("consecutive_losses", 0),
            "largest_win": self.risk_data.get("largest_win", 0),
            "largest_loss": self.risk_data.get("largest_loss", 0)
        }
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate percentage"""
        total = self.risk_data.get("trades_this_month", 0)
        if total == 0:
            return 0.0
        wins = self.risk_data.get("winning_trades", 0)
        return (wins / total) * 100
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate max drawdown for the month"""
        month_start = self.risk_data.get("month_start_equity", 0)
        month_low = self.risk_data.get("month_low_equity", month_start)
        if month_start > 0:
            return ((month_start - month_low) / month_start) * 100
        return 0.0
    
    def reset_daily_tracking(self, current_equity: float):
        """Reset daily equity tracking (call at start of each trading day)"""
        self.risk_data["daily_equity_start"] = current_equity
        self._save_risk_data()


def get_risk_manager(data_dir: str = "./data") -> ElderRiskManager:
    """Get singleton instance of risk manager"""
    return ElderRiskManager(data_dir)
