#!/usr/bin/env python3
"""
Test script to verify portfolio management upgrade
Checks that agent prompt includes all necessary portfolio management instructions
"""

from prompts.agent_prompt import get_agent_system_prompt, STOP_SIGNAL
from datetime import datetime

def test_portfolio_management_prompt():
    """Verify the agent prompt includes portfolio management features"""
    
    print("=" * 80)
    print("TESTING PORTFOLIO MANAGEMENT PROMPT")
    print("=" * 80)
    
    # Generate prompt
    today_date = datetime.now().strftime("%Y-%m-%d")
    signature = "test-portfolio-manager"
    prompt = get_agent_system_prompt(today_date, signature)
    
    print(f"\n📅 Test Date: {today_date}")
    print(f"🤖 Agent Signature: {signature}")
    print(f"📏 Prompt Length: {len(prompt)} characters\n")
    
    # Check for required portfolio management components
    checks = {
        "Mission Statement": [
            "ACTIVELY MANAGE",
            "portfolio manager",
            "position sizing discipline"
        ],
        "Portfolio Review Section": [
            "CRITICAL FIRST STEP",
            "get_portfolio_summary()",
            "get_positions()",
            "get_company_info(symbol)"
        ],
        "Position Sizing Rules": [
            "MAXIMUM per position: 20%",
            "NEW position sizing: 5-10%",
            "IDEAL diversification: 5-10 positions"
        ],
        "Profit Taking Rules": [
            "UP 20%+",
            "UP 50%+",
            "TAKE 50% PROFITS",
            "TAKE 75% PROFITS"
        ],
        "Risk Management Rules": [
            "DOWN 10%",
            "DOWN 15%",
            "DOWN 20%",
            "MUST sell"
        ],
        "Portfolio Rebalancing": [
            "Perform daily rebalancing",
            "Position >20%",
            "Position <3%",
            "Top 3 positions >60%"
        ],
        "4-Phase Workflow": [
            "PHASE 1: PORTFOLIO REVIEW",
            "PHASE 2: IDENTIFY NEW OPPORTUNITIES",
            "PHASE 3: EXECUTE PORTFOLIO CHANGES",
            "PHASE 4: FINAL PORTFOLIO CHECK"
        ],
        "Decision Framework": [
            "For EACH Existing Position, Ask",
            "Is this position profitable?",
            "What does recent news say?",
            "What % of portfolio is this?",
            "What's the price trend?"
        ],
        "MCP Tools": [
            "get_portfolio_summary()",
            "get_account()",
            "get_positions()",
            "close_position(symbol, percentage=50)",
            "get_company_info(symbol)",
            "search_news(query, max_results)"
        ]
    }
    
    results = {}
    all_passed = True
    
    print("🔍 Checking for required components:\n")
    
    for section, keywords in checks.items():
        print(f"📋 {section}:")
        section_passed = True
        missing = []
        
        for keyword in keywords:
            if keyword in prompt:
                print(f"   ✅ Found: {keyword}")
            else:
                print(f"   ❌ MISSING: {keyword}")
                section_passed = False
                missing.append(keyword)
                all_passed = False
        
        results[section] = {
            "passed": section_passed,
            "missing": missing
        }
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed_count = sum(1 for r in results.values() if r["passed"])
    total_count = len(results)
    
    print(f"\n✅ Passed: {passed_count}/{total_count} sections")
    print(f"❌ Failed: {total_count - passed_count}/{total_count} sections\n")
    
    if all_passed:
        print("🎉 SUCCESS! All portfolio management components are present!")
        print("\n✅ The agent prompt includes:")
        print("   • Portfolio review as first step")
        print("   • Position sizing rules (max 20%)")
        print("   • Profit taking rules (+20%, +50%)")
        print("   • Risk management rules (stop loss at -20%)")
        print("   • Portfolio rebalancing guidelines")
        print("   • 4-phase workflow (portfolio-first approach)")
        print("   • Decision-making framework for positions")
        print("   • All necessary MCP tools")
        print("\n🚀 The AI agent is ready to actively manage a portfolio!")
    else:
        print("⚠️ WARNING! Some components are missing:")
        for section, result in results.items():
            if not result["passed"]:
                print(f"\n❌ {section}:")
                for keyword in result["missing"]:
                    print(f"   - {keyword}")
        print("\n🔧 Please review prompts/agent_prompt.py")
    
    print("\n" + "=" * 80)
    
    # Additional checks
    print("\n🔍 Additional Verification:\n")
    
    # Check prompt structure
    if "PORTFOLIO MANAGEMENT RULES:" in prompt:
        print("✅ Portfolio management rules section exists")
    else:
        print("❌ Portfolio management rules section missing")
    
    if "TRADING WORKFLOW (PORTFOLIO-FIRST APPROACH):" in prompt:
        print("✅ Portfolio-first workflow exists")
    else:
        print("❌ Portfolio-first workflow missing")
    
    if "DECISION-MAKING FRAMEWORK:" in prompt:
        print("✅ Decision-making framework exists")
    else:
        print("❌ Decision-making framework missing")
    
    # Check for stop signal
    if STOP_SIGNAL in prompt:
        print(f"✅ Stop signal configured: {STOP_SIGNAL}")
    else:
        print("❌ Stop signal missing")
    
    # Count phases
    phase_count = prompt.count("PHASE")
    if phase_count >= 4:
        print(f"✅ Found {phase_count} workflow phases")
    else:
        print(f"⚠️ Only found {phase_count} workflow phases (expected 4+)")
    
    print("\n" + "=" * 80)
    
    return all_passed


def print_sample_prompt():
    """Print a sample section of the prompt"""
    today_date = datetime.now().strftime("%Y-%m-%d")
    signature = "test-agent"
    prompt = get_agent_system_prompt(today_date, signature)
    
    print("\n" + "=" * 80)
    print("SAMPLE PROMPT EXCERPT (First 1000 characters)")
    print("=" * 80)
    print(prompt[:1000])
    print("\n[... truncated ...]")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run tests
    success = test_portfolio_management_prompt()
    
    # Print sample
    print_sample_prompt()
    
    # Final status
    print("\n" + "=" * 80)
    if success:
        print("✅ PORTFOLIO MANAGEMENT UPGRADE VERIFIED")
        print("🚀 Ready to run: python main.py")
    else:
        print("❌ VERIFICATION FAILED")
        print("🔧 Please check prompts/agent_prompt.py")
    print("=" * 80)
    
    exit(0 if success else 1)
