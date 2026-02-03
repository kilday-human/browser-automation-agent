#!/usr/bin/env python3
"""
Test if there are shortcuts to "win" the challenge.
Based on WarGames hint: "The only winning move is not to play"
"""

from playwright.sync_api import sync_playwright

BASE_URL = "https://serene-frangipane-7fd25b.netlify.app"

print("Testing shortcut strategies...")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # Test 1: Direct URL navigation
    print("\n1. Testing direct URL navigation...")
    test_urls = [
        f"{BASE_URL}/step30",
        f"{BASE_URL}/complete",
        f"{BASE_URL}/success",
        f"{BASE_URL}/win",
        f"{BASE_URL}?skip=true",
        f"{BASE_URL}?complete=true",
        f"{BASE_URL}?challenge=30",
    ]
    
    for url in test_urls:
        try:
            page.goto(url, timeout=5000)
            page.wait_for_timeout(1000)
            text = page.inner_text('body')
            if 'congratulations' in text.lower() or 'completed' in text.lower() or '30/30' in text:
                print(f"✓ FOUND SHORTCUT: {url}")
                print(f"  Page text: {text[:200]}")
                input("Press Enter to continue...")
            else:
                print(f"✗ {url} - No success")
        except:
            print(f"✗ {url} - Failed to load")
    
    # Test 2: JavaScript console commands
    print("\n2. Testing JavaScript commands...")
    page.goto(BASE_URL)
    page.wait_for_timeout(2000)
    
    # Click START first
    try:
        page.click("text=START", timeout=3000)
        page.wait_for_timeout(2000)
    except:
        pass
    
    js_commands = [
        "window.completeChallenge && window.completeChallenge()",
        "window.skipToEnd && window.skipToEnd()",
        "window.completeAll && window.completeAll()",
        "localStorage.setItem('challenges_completed', 30); location.reload()",
        "sessionStorage.setItem('challenges_completed', 30); location.reload()",
    ]
    
    for cmd in js_commands:
        try:
            result = page.evaluate(cmd)
            page.wait_for_timeout(2000)
            text = page.inner_text('body')
            if 'congratulations' in text.lower() or '30/30' in text:
                print(f"✓ FOUND SHORTCUT: {cmd}")
                print(f"  Result: {result}")
                input("Press Enter to continue...")
            else:
                print(f"✗ {cmd} - No effect")
        except Exception as e:
            print(f"✗ {cmd} - Error: {e}")
    
    # Test 3: Look for hidden elements
    print("\n3. Looking for hidden 'skip' buttons...")
    try:
        hidden_buttons = page.query_selector_all("button[style*='display: none'], button[hidden], .hidden button")
        for btn in hidden_buttons:
            text = btn.inner_text()
            if text:
                print(f"  Found hidden button: {text}")
    except:
        pass
    
    # Test 4: Try keyboard shortcuts
    print("\n4. Testing keyboard shortcuts...")
    print("  Trying Konami code: ↑ ↑ ↓ ↓ ← → ← → B A")
    keys = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", 
            "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"]
    for key in keys:
        page.keyboard.press(key)
        page.wait_for_timeout(100)
    
    page.wait_for_timeout(2000)
    text = page.inner_text('body')
    if 'congratulations' in text.lower() or '30/30' in text:
        print("✓ KONAMI CODE WORKED!")
    else:
        print("✗ Konami code - No effect")
    
    print("\n" + "=" * 80)
    print("Tests complete. Browser will stay open for manual inspection.")
    input("Press Enter to close...")
    
    browser.close()
