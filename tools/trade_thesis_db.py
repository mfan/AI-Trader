"""
Trade Thesis Database Manager

Stores trading thesis, analysis, support/resistance, stop loss, and target prices
for each trade to enforce disciplined trading strategy.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class TradeThesisDB:
    """Manages trade thesis and price targets in SQLite database"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file (default: data/trade_thesis.db)
        """
        if db_path is None:
            # Default to data directory
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "trade_thesis.db")
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Trade thesis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_thesis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL,
                
                -- Trading thesis and analysis
                thesis TEXT NOT NULL,
                market_regime TEXT,
                technical_setup TEXT,
                
                -- Price levels
                support_price REAL NOT NULL,
                resistance_price REAL NOT NULL,
                stop_loss_price REAL NOT NULL,
                target_price REAL NOT NULL,
                
                -- Trade metadata
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                status TEXT DEFAULT 'OPEN',
                
                -- Exit details
                exit_price REAL,
                exit_reason TEXT,
                pnl REAL,
                pnl_percent REAL,
                
                -- Additional context
                confidence_level INTEGER,
                risk_reward_ratio REAL,
                notes TEXT
            )
        """)
        
        # Price level checks table (log when prices are checked)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                current_price REAL NOT NULL,
                target_distance REAL,
                stop_distance REAL,
                recommendation TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES trade_thesis(order_id)
            )
        """)
        
        self.conn.commit()
    
    def add_trade_thesis(
        self,
        order_id: str,
        symbol: str,
        action: str,
        quantity: float,
        thesis: str,
        support_price: float,
        resistance_price: float,
        stop_loss_price: float,
        target_price: float,
        entry_price: float = None,
        market_regime: str = None,
        technical_setup: str = None,
        confidence_level: int = None,
        notes: str = None
    ) -> bool:
        """
        Add a new trade thesis to the database
        
        Args:
            order_id: Alpaca order ID
            symbol: Stock symbol
            action: Trade action (BUY, SHORT, SELL)
            quantity: Number of shares
            thesis: Trading thesis explaining why entering this trade
            support_price: Support level (floor)
            resistance_price: Resistance level (ceiling)
            stop_loss_price: Price to exit if trade goes against us
            target_price: Price to exit when target is reached
            entry_price: Actual entry price (if known)
            market_regime: Current market regime (BULLISH, BEARISH, NEUTRAL)
            technical_setup: Technical analysis setup description
            confidence_level: Confidence in trade (1-5, 5 being highest)
            notes: Additional notes
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Calculate risk/reward ratio
            if entry_price and stop_loss_price and target_price:
                risk = abs(entry_price - stop_loss_price)
                reward = abs(target_price - entry_price)
                risk_reward_ratio = reward / risk if risk > 0 else 0
            else:
                risk_reward_ratio = None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO trade_thesis (
                    order_id, symbol, action, quantity, entry_price,
                    thesis, market_regime, technical_setup,
                    support_price, resistance_price, stop_loss_price, target_price,
                    confidence_level, risk_reward_ratio, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, symbol, action, quantity, entry_price,
                thesis, market_regime, technical_setup,
                support_price, resistance_price, stop_loss_price, target_price,
                confidence_level, risk_reward_ratio, notes
            ))
            
            self.conn.commit()
            print(f"✅ Trade thesis saved for {symbol} (Order: {order_id})")
            return True
            
        except sqlite3.IntegrityError:
            print(f"⚠️ Trade thesis already exists for order {order_id}")
            return False
        except Exception as e:
            print(f"❌ Error saving trade thesis: {e}")
            return False
    
    def check_price_action(
        self,
        symbol: str,
        current_price: float
    ) -> Dict[str, Any]:
        """
        Check if current price has reached stop loss or target for open positions
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
            
        Returns:
            Dict with recommendations for each open position
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM trade_thesis
            WHERE symbol = ? AND status = 'OPEN'
            ORDER BY opened_at DESC
        """, (symbol,))
        
        positions = cursor.fetchall()
        recommendations = []
        
        for pos in positions:
            pos_dict = dict(pos)
            
            # Calculate distances
            target_distance = abs(current_price - pos_dict['target_price'])
            stop_distance = abs(current_price - pos_dict['stop_loss_price'])
            
            # Determine action
            action = pos_dict['action']
            
            if action in ['BUY', 'LONG']:
                # Long position
                if current_price <= pos_dict['stop_loss_price']:
                    recommendation = f"🚨 STOP LOSS HIT - SELL IMMEDIATELY at ${current_price:.2f}"
                    should_exit = True
                    reason = "STOP_LOSS"
                elif current_price >= pos_dict['target_price']:
                    recommendation = f"🎯 TARGET REACHED - SELL at ${current_price:.2f}"
                    should_exit = True
                    reason = "TARGET_REACHED"
                else:
                    recommendation = f"✅ HOLD - Price ${current_price:.2f} between stop ${pos_dict['stop_loss_price']:.2f} and target ${pos_dict['target_price']:.2f}"
                    should_exit = False
                    reason = "HOLD"
                    
            elif action in ['SHORT', 'SELL']:
                # Short position
                if current_price >= pos_dict['stop_loss_price']:
                    recommendation = f"🚨 STOP LOSS HIT - COVER SHORT IMMEDIATELY at ${current_price:.2f}"
                    should_exit = True
                    reason = "STOP_LOSS"
                elif current_price <= pos_dict['target_price']:
                    recommendation = f"🎯 TARGET REACHED - COVER SHORT at ${current_price:.2f}"
                    should_exit = True
                    reason = "TARGET_REACHED"
                else:
                    recommendation = f"✅ HOLD - Price ${current_price:.2f} between target ${pos_dict['target_price']:.2f} and stop ${pos_dict['stop_loss_price']:.2f}"
                    should_exit = False
                    reason = "HOLD"
            
            # Log the price check
            cursor.execute("""
                INSERT INTO price_checks (
                    order_id, symbol, current_price, target_distance, stop_distance, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pos_dict['order_id'], symbol, current_price,
                target_distance, stop_distance, recommendation
            ))
            
            recommendations.append({
                'order_id': pos_dict['order_id'],
                'symbol': symbol,
                'action': action,
                'quantity': pos_dict['quantity'],
                'entry_price': pos_dict['entry_price'],
                'current_price': current_price,
                'stop_loss_price': pos_dict['stop_loss_price'],
                'target_price': pos_dict['target_price'],
                'support_price': pos_dict['support_price'],
                'resistance_price': pos_dict['resistance_price'],
                'thesis': pos_dict['thesis'],
                'recommendation': recommendation,
                'should_exit': should_exit,
                'exit_reason': reason,
                'opened_at': pos_dict['opened_at']
            })
        
        self.conn.commit()
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'positions': recommendations,
            'total_positions': len(recommendations)
        }
    
    def close_trade(
        self,
        order_id: str,
        exit_price: float,
        exit_reason: str,
        pnl: float = None,
        pnl_percent: float = None
    ) -> bool:
        """
        Mark a trade as closed
        
        Args:
            order_id: Original order ID
            exit_price: Exit price
            exit_reason: Reason for exit (STOP_LOSS, TARGET_REACHED, MANUAL, etc.)
            pnl: Profit/loss in dollars
            pnl_percent: Profit/loss percentage
            
        Returns:
            bool: True if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE trade_thesis
                SET status = 'CLOSED',
                    closed_at = CURRENT_TIMESTAMP,
                    exit_price = ?,
                    exit_reason = ?,
                    pnl = ?,
                    pnl_percent = ?
                WHERE order_id = ?
            """, (exit_price, exit_reason, pnl, pnl_percent, order_id))
            
            self.conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✅ Trade closed for order {order_id} - Reason: {exit_reason}")
                return True
            else:
                print(f"⚠️ No open trade found for order {order_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error closing trade: {e}")
            return False
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions with their thesis and price levels"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM trade_thesis
            WHERE status = 'OPEN'
            ORDER BY opened_at DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_trade_history(self, symbol: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trade history"""
        cursor = self.conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT * FROM trade_thesis
                WHERE symbol = ?
                ORDER BY opened_at DESC
                LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT * FROM trade_thesis
                ORDER BY opened_at DESC
                LIMIT ?
            """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics"""
        cursor = self.conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                AVG(pnl) as avg_pnl,
                SUM(pnl) as total_pnl,
                AVG(risk_reward_ratio) as avg_risk_reward
            FROM trade_thesis
        """)
        
        stats = dict(cursor.fetchone())
        
        # Exit reasons breakdown
        cursor.execute("""
            SELECT exit_reason, COUNT(*) as count
            FROM trade_thesis
            WHERE status = 'CLOSED'
            GROUP BY exit_reason
        """)
        
        exit_reasons = {row['exit_reason']: row['count'] for row in cursor.fetchall()}
        stats['exit_reasons'] = exit_reasons
        
        return stats
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Singleton instance
_db_instance = None

def get_trade_thesis_db() -> TradeThesisDB:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradeThesisDB()
    return _db_instance
