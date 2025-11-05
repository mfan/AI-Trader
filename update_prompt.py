#!/usr/bin/env python3
"""
Script to update agent_prompt.py to remove extended hours trading references.
This avoids Unicode character matching issues by reading and rewriting the file.
"""

def update_agent_prompt():
    prompt_file = '/home/mfan/work/aitrader/prompts/agent_prompt.py'
    
    # Read the current content
    with open(prompt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Track changes
    changes_made = []
    
    # Process line by line
    for i, line in enumerate(lines, 1):
        original = line
        
        # Replace extended hours references
        if 'EXTENDED HOURS' in line:
            line = line.replace('EXTENDED HOURS DAY TRADING', 'DAY TRADING (Regular Hours Only)')
            line = line.replace('EXTENDED HOURS', 'REGULAR HOURS')
        
        # Update time references
        if '4:00 AM' in line or '4:00AM' in line:
            line = line.replace('4:00 AM', '9:30 AM').replace('4:00AM', '9:30AM')
        
        if '8:00 PM' in line or '8:00PM' in line:
            line = line.replace('8:00 PM', '4:00 PM').replace('8:00PM', '4:00PM')
        
        if '7:55 PM' in line or '7:55PM' in line:
            line = line.replace('7:55 PM', '3:55 PM').replace('7:55PM', '3:55PM')
        
        # Update session references
        if 'pre-market' in line.lower() or 'premarket' in line.lower():
            if 'PRE-MARKET' in line:
                line = line.replace('PRE-MARKET', 'REGULAR MARKET')
            elif 'Pre-Market' in line:
                line = line.replace('Pre-Market', 'Regular Market')
            else:
                line = line.replace('pre-market', 'regular market').replace('premarket', 'regular market')
        
        if 'post-market' in line.lower() or 'postmarket' in line.lower():
            if 'POST-MARKET' in line:
                line = line.replace('POST-MARKET', 'REGULAR MARKET')
            elif 'Post-Market' in line:
                line = line.replace('Post-Market', 'Regular Market')
            else:
                line = line.replace('post-market', 'regular market').replace('postmarket', 'regular market')
        
        # Track if line was changed
        if line != original:
            changes_made.append((i, original.strip(), line.strip()))
        
        lines[i-1] = line
    
    # Write back the updated content
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Print summary
    print(f"✅ Updated {prompt_file}")
    print(f"\n📝 Made {len(changes_made)} changes:\n")
    for line_num, old, new in changes_made[:10]:  # Show first 10
        print(f"Line {line_num}:")
        print(f"  OLD: {old[:100]}...")
        print(f"  NEW: {new[:100]}...")
        print()
    
    if len(changes_made) > 10:
        print(f"... and {len(changes_made) - 10} more changes")
    
    return len(changes_made)

if __name__ == '__main__':
    changes = update_agent_prompt()
    print(f"\n✅ Complete! {changes} lines updated.")
    print("\n⚠️  NOTE: You may want to review the changes manually to ensure")
    print("   all extended hours references are properly removed.")
