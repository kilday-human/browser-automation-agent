"""Browser automation abstractions using Playwright."""

import re
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser, Playwright


class BrowserController:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    def start(self) -> "BrowserController":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        return self

    def close(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser not started")
        return self._page

    def goto(self, url: str, timeout: int = 30000):
        self.page.goto(url, timeout=timeout, wait_until="networkidle")

    def get_text(self) -> str:
        """Get visible text content of the page."""
        return self.page.inner_text("body")

    def get_html(self, selector: str = "body") -> str:
        """Get HTML of an element."""
        return self.page.inner_html(selector)

    def get_dom_snapshot(self, max_length: int = 8000) -> str:
        """Get a cleaned DOM snapshot for LLM consumption."""
        html = self.page.content()
        # Strip scripts, styles, and excessive whitespace
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
        html = re.sub(r"\s+", " ", html)
        return html[:max_length]

    def get_interactive_elements(self) -> list[dict]:
        """Get all interactive elements with their properties."""
        elements = []
        for el in self.page.query_selector_all("button, input, textarea, select, a, [onclick], [role='button']"):
            try:
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                text = el.inner_text()[:100] if el.inner_text() else ""
                placeholder = el.get_attribute("placeholder") or ""
                value = el.get_attribute("value") or ""
                el_id = el.get_attribute("id") or ""
                el_class = el.get_attribute("class") or ""
                el_type = el.get_attribute("type") or ""
                disabled = el.is_disabled() if tag in ["button", "input", "select", "textarea"] else False
                
                elements.append({
                    "tag": tag,
                    "text": text.strip(),
                    "placeholder": placeholder,
                    "value": value,
                    "id": el_id,
                    "class": el_class,
                    "type": el_type,
                    "disabled": disabled,
                    "selector": self._build_selector(tag, el_id, el_class, text),
                })
            except:
                continue
        return elements

    def _build_selector(self, tag: str, el_id: str, el_class: str, text: str) -> str:
        """Build a reliable selector for an element."""
        if el_id:
            return f"#{el_id}"
        if text and len(text) < 50:
            return f'{tag}:has-text("{text[:30]}")'
        if el_class:
            first_class = el_class.split()[0]
            return f"{tag}.{first_class}"
        return tag

    def click(self, selector: str, timeout: int = 5000):
        """Click an element by selector."""
        self.page.click(selector, timeout=timeout)

    def click_text(self, text: str, exact: bool = False, timeout: int = 5000):
        """Click an element containing specific text."""
        if exact:
            self.page.get_by_text(text, exact=True).click(timeout=timeout)
        else:
            self.page.get_by_text(text).first.click(timeout=timeout)

    def click_button(self, text: str, timeout: int = 5000):
        """Click a button by its text."""
        self.page.get_by_role("button", name=text).click(timeout=timeout)

    def type_text(self, selector: str, text: str, clear: bool = True):
        """Type text into an input field."""
        if clear:
            self.page.fill(selector, text)
        else:
            self.page.type(selector, text)

    def type_into_placeholder(self, placeholder: str, text: str):
        """Type into an input by its placeholder."""
        self.page.get_by_placeholder(placeholder).fill(text)

    def type_into_label(self, label: str, text: str):
        """Type into an input by its label."""
        self.page.get_by_label(label).fill(text)

    def press_key(self, key: str):
        """Press a keyboard key."""
        self.page.keyboard.press(key)
    
    def scroll_down(self, pixels: int = 500):
        """Scroll down by specified pixels."""
        self.page.evaluate(f"window.scrollBy(0, {pixels})")
        self.page.wait_for_timeout(300)  # Wait for scroll animation
    
    def scroll_to_bottom(self):
        """Scroll to bottom of page."""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(300)

    def select_option(self, selector: str, value: str):
        """Select an option from a dropdown."""
        self.page.select_option(selector, value)

    def wait_for_selector(self, selector: str, timeout: int = 5000):
        """Wait for an element to appear."""
        self.page.wait_for_selector(selector, timeout=timeout)

    def wait_for_text(self, text: str, timeout: int = 5000):
        """Wait for text to appear on page."""
        self.page.wait_for_selector(f'text="{text}"', timeout=timeout)

    def wait_for_network_idle(self, timeout: int = 5000):
        """Wait for network to be idle (no pending requests)."""
        self.page.wait_for_load_state("networkidle", timeout=timeout)

    def wait_for_dom_stable(self, timeout: int = 3000, check_interval: int = 200):
        """Wait until DOM stops changing (for SPAs/dynamic content)."""
        import time as t
        last_html = ""
        start = t.time()
        while (t.time() - start) * 1000 < timeout:
            current_html = self.page.content()
            if current_html == last_html:
                return True
            last_html = current_html
            self.page.wait_for_timeout(check_interval)
        return False

    def wait_for_no_spinners(self, timeout: int = 5000):
        """Wait for loading indicators to disappear."""
        spinner_selectors = [
            ".loading", ".spinner", "[class*='load']", "[class*='spin']",
            "[aria-busy='true']", ".skeleton", "[class*='skeleton']"
        ]
        for selector in spinner_selectors:
            try:
                self.page.wait_for_selector(selector, state="hidden", timeout=timeout)
            except:
                pass

    def take_screenshot_base64(self) -> str:
        """Take screenshot and return as base64 for vision models."""
        import base64
        screenshot_bytes = self.page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    def screenshot(self, path: str):
        """Take a screenshot."""
        self.page.screenshot(path=path)

    def evaluate(self, script: str):
        """Run JavaScript in the page context."""
        return self.page.evaluate(script)

    def find_by_text(self, text: str) -> bool:
        """Check if text exists on page."""
        return text.lower() in self.get_text().lower()

    def get_input_value(self, selector: str) -> str:
        """Get the value of an input field."""
        return self.page.input_value(selector)
    
    def find_data_attributes(self, attribute_pattern: str = "data-challenge-code") -> dict:
        """Find all elements with specific data attributes and their values."""
        script = f"""
        () => {{
            const results = {{}};
            const elements = document.querySelectorAll('[{attribute_pattern}]');
            elements.forEach((el, i) => {{
                results[`element_${{i}}`] = el.getAttribute('{attribute_pattern}');
            }});
            return results;
        }}
        """
        return self.page.evaluate(script)

    def dismiss_popups(self) -> int:
        """Try to dismiss any visible popups/modals. Returns number dismissed."""
        dismissed = 0
        
        # PRIORITY 1: Cookie consent MUST be clicked first (blocks other popups)
        try:
            accept_buttons = self.page.locator("button:has-text('Accept')").all()
            for btn in accept_buttons:
                if btn.is_visible():
                    btn.click(timeout=1000, force=True)
                    dismissed += 1
                    self.page.wait_for_timeout(500)
                    break
        except:
            pass
        
        # PRIORITY 2: Target the REAL grey X button in top-right corner
        # These close buttons typically have:
        # - position: absolute
        # - Small size (20-40px square)
        # - Top-right positioning (top: 0-20px, right: 0-20px)
        # - Text content is just "×" or "X"
        close_button_selectors = [
            # Top-right positioned X buttons (most specific - target the GREY X)
            "button[style*='position: absolute'][style*='top'][style*='right']:has-text('×')",
            "button[style*='position: absolute'][style*='top'][style*='right']:has-text('✕')",
            "button[style*='position: absolute'][style*='top'][style*='right']:has-text('X')",
            
            # Buttons with absolute positioning and X symbols
            "button.absolute:has-text('×')",
            "button.absolute:has-text('✕')",
            "button.absolute:has-text('✖')",
            
            # Buttons in top-right corner (by class)
            "button[class*='top-'][class*='right']:has-text('×')",
            "button[class*='top-'][class*='right']:has-text('X')",
            
            # Close button classes
            "button[class*='close']:has-text('×')",
            "button[class*='close']:has-text('X')",
            "button.modal-close",
            
            # Aria label close buttons
            "button[aria-label*='close' i]",
            "button[aria-label*='dismiss' i]",
            
            # Just X symbols (but not in challenge text)
            "button:has-text('×'):not(:has-text('Step')):not(:has-text('Challenge'))",
            "button:has-text('✕'):not(:has-text('Step')):not(:has-text('Challenge'))",
            
            # Last resort: any button with just X
            "button:text-is('×')",
            "button:text-is('X')",
        ]
        
        # Try dismissing up to 25 popups (they reappear!)
        for attempt in range(25):
            found_any = False
            
            # Try each selector strategy
            for selector in close_button_selectors:
                try:
                    # Find all matching buttons
                    buttons = self.page.locator(selector).all()
                    for btn in buttons:
                        if btn.is_visible():
                            # Click with force=True to override fake overlays
                            btn.click(timeout=1000, force=True)
                            dismissed += 1
                            found_any = True
                            self.page.wait_for_timeout(300)  # Wait for popup to close
                            break  # Try next selector after successful click
                    
                    if found_any:
                        break  # Move to next attempt
                except:
                    continue
            
            if not found_any:
                break  # No more popups to dismiss
        
        return dismissed