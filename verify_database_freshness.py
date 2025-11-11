#!/usr/bin/env python3
"""
Database Freshness Verification Script

Verifies that momentum cache database is properly updated daily:
1. Old data is flushed when new scan runs
2. Timestamps are current
3. Scan date is yesterday's close
4. Only latest data is retained
"""

import sys
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data/agent_data/xai-grok-4-latest/momentum_cache.db"


def verify_database():
    """Verify database freshness and update behavior."""
    
    print("=" * 80)
    print("DATABASE FRESHNESS VERIFICATION")
    print("=" * 80)
    print(f"Database: {DB_PATH}\n")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Check all scan dates (should only have recent ones)
        print("📅 SCAN DATES IN DATABASE:")
        cursor.execute("""
            SELECT 
                scan_date,
                COUNT(*) as rows,
                MIN(created_at) as first_cached,
                MAX(updated_at) as last_updated
            FROM daily_movers 
            GROUP BY scan_date 
            ORDER BY scan_date DESC
        """)
        
        dates = cursor.fetchall()
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        if not dates:
            print("   ❌ NO DATA FOUND")
            return False
        
        for scan_date, rows, created, updated in dates:
            status = ""
            if scan_date == yesterday:
                status = "✅ YESTERDAY (CORRECT)"
            elif scan_date == today:
                status = "⚠️  TODAY (Should be yesterday)"
            else:
                status = "⚠️  OLD DATA"
            
            print(f"   {scan_date}: {rows} rows | Created: {created} | Updated: {updated}")
            print(f"              {status}\n")
        
        # 2. Check if data is fresh (created/updated today)
        print("\n⏰ TIMESTAMP FRESHNESS:")
        latest_scan = dates[0][0]
        
        cursor.execute("""
            SELECT 
                MIN(created_at) as earliest_created,
                MAX(created_at) as latest_created,
                MIN(updated_at) as earliest_updated,
                MAX(updated_at) as latest_updated
            FROM daily_movers
            WHERE scan_date = ?
        """, (latest_scan,))
        
        timestamps = cursor.fetchone()
        created_date = timestamps[0].split()[0] if timestamps[0] else None
        updated_date = timestamps[2].split()[0] if timestamps[2] else None
        
        print(f"   Latest Scan Date: {latest_scan}")
        print(f"   Created Range:    {timestamps[0]} to {timestamps[1]}")
        print(f"   Updated Range:    {timestamps[2]} to {timestamps[3]}")
        
        if created_date == today and updated_date == today:
            print(f"   Status: ✅ FRESH (Cached today: {today})")
        else:
            print(f"   Status: ⚠️  STALE (Not cached today)")
        
        # 3. Verify scan date is yesterday
        print(f"\n📊 DATA VALIDITY:")
        print(f"   Today:     {today}")
        print(f"   Yesterday: {yesterday}")
        print(f"   Scan Date: {latest_scan}")
        
        if latest_scan == yesterday:
            print(f"   Status: ✅ CORRECT (Using yesterday's close for today's strategy)")
        elif latest_scan == today:
            print(f"   Status: ⚠️  INCORRECT (Should use yesterday, not today)")
        else:
            print(f"   Status: ❌ OUTDATED (Data is {(datetime.now() - datetime.strptime(latest_scan, '%Y-%m-%d')).days} days old)")
        
        # 4. Check for data accumulation (should have max ~30 days)
        cursor.execute("SELECT COUNT(DISTINCT scan_date) FROM daily_movers")
        unique_dates = cursor.fetchone()[0]
        
        print(f"\n🗄️  DATA RETENTION:")
        print(f"   Unique Scan Dates: {unique_dates}")
        
        if unique_dates == 1:
            print(f"   Status: ✅ OPTIMAL (Only latest scan retained)")
        elif unique_dates <= 30:
            print(f"   Status: ✅ GOOD (Within 30-day cleanup policy)")
        else:
            print(f"   Status: ⚠️  ACCUMULATING (Consider running cleanup)")
        
        # 5. Verify DELETE behavior (check if scan_date is unique)
        cursor.execute("""
            SELECT scan_date, COUNT(*) as duplicates
            FROM daily_movers
            GROUP BY scan_date, symbol
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        
        print(f"\n🔄 DATA FLUSH VERIFICATION:")
        if duplicates:
            print(f"   ❌ DUPLICATES FOUND: {len(duplicates)} symbols have duplicate entries")
            print(f"   This means DELETE is not working properly!")
        else:
            print(f"   ✅ NO DUPLICATES (DELETE working correctly)")
        
        # 6. Summary
        print(f"\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        issues = []
        if latest_scan != yesterday:
            issues.append("Scan date is not yesterday")
        if created_date != today:
            issues.append("Data not cached today")
        if unique_dates > 30:
            issues.append(f"Too many old scans ({unique_dates})")
        if duplicates:
            issues.append("Duplicate entries detected")
        
        if not issues:
            print("✅ ALL CHECKS PASSED")
            print("   • Data is from yesterday's close")
            print("   • Cached today (timestamps fresh)")
            print("   • Old data properly flushed")
            print("   • No duplicates detected")
        else:
            print("⚠️  ISSUES DETECTED:")
            for issue in issues:
                print(f"   • {issue}")
        
        conn.close()
        return len(issues) == 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    success = verify_database()
    sys.exit(0 if success else 1)
