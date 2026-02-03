#!/usr/bin/env python3
"""
Diagnostic script to see what Challenge 1 actually looks like.
Shows the real DOM structure and interactive elements.
"""

from playwright.sync_api import sync_playwright

print("Launching browser to inspect Challenge 1...")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("Navigating to challenge URL...")
    page.goto('https://serene-frangipane-7fd25b.netlify.app')
    page.wait_for_timeout(3000)
    
    print("\n=== PAGE TEXT (first 2000 chars) ===")
    text = page.inner_text('body')
    print(text[:2000])
    
    print("\n=== INTERACTIVE ELEMENTS ===")
    elements = page.query_selector_all('button, input, a, select, textarea')
    for i, el in enumerate(elements[:50], 1):  # Limit to 50 elements
        try:
            tag = el.evaluate("e => e.tagName")
            text = el.inner_text()[:50] if el.inner_text() else ""
            placeholder = el.get_attribute("placeholder") or ""
            el_id = el.get_attribute("id") or ""
            el_class = el.get_attribute("class") or ""
            visible = el.is_visible()
            
            info = f"{i}. <{tag}>"
            if text:
                info += f' text="{text}"'
            if placeholder:
                info += f' placeholder="{placeholder}"'
            if el_id:
                info += f' id="{el_id}"'
            if el_class:
                info += f' class="{el_class[:50]}"'
            info += f' visible={visible}'
            
            print(info)
        except:
            continue
    
    print("\n=== CHALLENGE NUMBER DETECTION TEST ===")
    import re
    
    # Test different regex patterns
    patterns = [
        (r"step\s+(\d+)\s+of\s+30", "Step X of 30"),
        (r"^(\d+)\s*(?:of|/)\s*30", "X of 30 or X/30"),
        (r"(?:challenge|task|level|question)\s*[#:]?\s*(\d+)", "Challenge #X"),
    ]
    
    for pattern, desc in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            print(f"✓ Pattern '{desc}' matched: {match.group(1)}")
        else:
            print(f"✗ Pattern '{desc}' NO MATCH")
    
    print("\n=== HTML STRUCTURE (first 1000 chars) ===")
    html = page.content()
    print(html[:1000])
    
    print("\n" + "=" * 80)
    print("Browser window is open. Inspect the page, then press Enter to close...")
    input()
    
    browser.close()
    print("Done!")
