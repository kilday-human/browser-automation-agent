#!/usr/bin/env python3
"""
Inspect popup close buttons to find the exact selectors.
This shows what the "grey X in top right" actually looks like in the DOM.
"""

from playwright.sync_api import sync_playwright
import json

print("Inspecting popup close buttons...")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("Navigating to challenge...")
    page.goto('https://serene-frangipane-7fd25b.netlify.app')
    page.wait_for_timeout(3000)
    
    # Click START if present
    try:
        page.locator("text=START").click(timeout=2000)
        print("✓ Clicked START button")
        page.wait_for_timeout(2000)
    except:
        print("No START button found")
    
    print("\n=== ANALYZING POPUP CLOSE BUTTONS ===")
    
    # JavaScript to find all potential close buttons
    close_button_info = page.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const closeButtons = [];
            
            buttons.forEach((btn, i) => {
                const text = btn.textContent.trim();
                const style = window.getComputedStyle(btn);
                const rect = btn.getBoundingClientRect();
                
                // Look for buttons that might be close buttons
                if (text === '×' || text === '✕' || text === '✖' || text === 'X' || 
                    btn.getAttribute('aria-label')?.includes('close') ||
                    btn.className.includes('close')) {
                    
                    closeButtons.push({
                        index: i,
                        text: text,
                        className: btn.className,
                        id: btn.id,
                        position: style.position,
                        top: style.top,
                        right: style.right,
                        width: style.width,
                        height: style.height,
                        visible: rect.width > 0 && rect.height > 0,
                        rect: {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        },
                        ariaLabel: btn.getAttribute('aria-label'),
                        selector: `button:nth-of-type(${i+1})`
                    });
                }
            });
            
            return closeButtons;
        }
    """)
    
    print(f"\nFound {len(close_button_info)} potential close buttons:")
    print(json.dumps(close_button_info, indent=2))
    
    print("\n=== VISIBLE POPUPS/MODALS ===")
    modals = page.evaluate("""
        () => {
            const modals = [];
            const elements = document.querySelectorAll('[class*="modal"], [class*="popup"], [class*="dialog"]');
            
            elements.forEach((el, i) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                
                if (rect.width > 0 && rect.height > 0) {
                    modals.push({
                        index: i,
                        className: el.className,
                        id: el.id,
                        zIndex: style.zIndex,
                        visible: style.display !== 'none' && style.visibility !== 'hidden',
                        text: el.textContent.substring(0, 100)
                    });
                }
            });
            
            return modals;
        }
    """)
    
    print(f"Found {len(modals)} visible modals:")
    print(json.dumps(modals, indent=2))
    
    print("\n" + "=" * 80)
    print("INSTRUCTIONS:")
    print("1. Look at the browser window")
    print("2. Find the GREY X button in the top-right of any popup")
    print("3. Right-click it and inspect element")
    print("4. Note the exact CSS selector")
    print("\nPress Enter when done...")
    input()
    
    browser.close()
    print("Done!")
