import json
import time
import pyautogui
import sys
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import cv2
import numpy as np

class ElementNotFoundError(Exception):
    def __init__(self, message="Can't find the element"):
        self.message = message
        super().__init__(self.message)

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def open_url(driver, url):
    driver.get(url)

def new_tab(driver):
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])

def close_tab(driver):
    driver.close()
    driver.switch_to.window(driver.window_handles[-1])

def reload_page(driver):
    driver.refresh()

def go_back(driver):
    driver.back()

def mouse_click(x, y):
    pyautogui.click(x, y)

def mouse_press_and_hold(x, y, duration=2):
    pyautogui.mouseDown(x, y)
    time.sleep(duration)
    pyautogui.mouseUp(x, y)

def mouse_move(x, y):
    pyautogui.moveTo(x, y)

def mouse_scroll(amount):
    pyautogui.scroll(amount)

def keyboard_press(key):
    pyautogui.press(key)

def keyboard_hold(key, duration=2):
    pyautogui.keyDown(key)
    time.sleep(duration)
    pyautogui.keyUp(key)

def keyboard_type(text):
    pyautogui.write(text, interval=0.05)

def locate_and_click_element(driver, xpath):
    try:
        element = None
        
        # Wait for the element to be present in the DOM
        try:
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        except:
            print("Element not found via standard WebDriver method. Trying JavaScript...")
            element = driver.execute_script(
                "return document.evaluate(arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;",
                xpath
            )
        
        # Handle dynamically loaded elements inside iframes
        if element is None:
            print("Checking for iframes...")
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                driver.switch_to.frame(iframe)
                try:
                    element = driver.find_element(By.XPATH, xpath)
                    if element:
                        break
                except:
                    driver.switch_to.default_content()
            driver.switch_to.default_content()
        
        if element:
            is_enabled = driver.execute_script("return !arguments[0].disabled && arguments[0].offsetParent !== null;", element)
            if is_enabled:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(1)
                driver.execute_script("arguments[0].style.border='3px solid red'", element)
                rect = driver.execute_script("return arguments[0].getBoundingClientRect();", element)
                window_x = driver.execute_script("return window.screenX;")
                window_y = driver.execute_script("return window.screenY;")

                # Get browser UI offset (tabs, search bar)
                browser_ui_offset = driver.execute_script("return window.outerHeight - window.innerHeight;")

                # Adjust y-coordinate to include browser UI
                x = window_x + rect['left'] + rect['width'] / 2
                y = window_y + browser_ui_offset + rect['top'] + rect['height'] / 2

                # Ensure clicking works properly
                driver.execute_script("arguments[0].focus();", element)
                driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));", element)
                print(f"Element Clicked at: X={x}, Y={y}")
                return int(x), int(y)
            else:
                print("Element is either disabled or not visible for clicking.")
                return None, None
    except Exception as e:
        print(f"Error finding or clicking element: {e}")
    return None, None

def get_browser_position(driver):
    x = driver.execute_script("return window.screenX;")  # Output: 0
    y = driver.execute_script("return window.screenY;")  # Output: 0
    return x, y

def get_valid_selectors(driver):
    try:
        script = """
        function getAllTags(root) {
            let tags = new Set(Array.from(root.querySelectorAll('*')).map(el => el.tagName.toLowerCase()));
            let shadowHosts = root.querySelectorAll('*');
            for (let host of shadowHosts) {
                if (host.shadowRoot) {
                    let shadowTags = getAllTags(host.shadowRoot);
                    shadowTags.forEach(tag => tags.add(tag));
                }
            }
            return Array.from(tags);
        }
        return getAllTags(document);
        """
        return driver.execute_script(script)
    except Exception as e:
        print(f"Error retrieving valid selectors: {e}")
        return []

def check_by_image(input_image_path, threshold = 0.8 ):
    try:
        screenshot = pyautogui.screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        input_image = cv2.imread(input_image_path, cv2.IMREAD_COLOR)
        if input_image is None:
            print("Error: Input image not found.")
            return None
        
        result = cv2.matchTemplate(screenshot, input_image, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            print(f"Image found at: {max_loc}")
            return max_loc  # Returns the top-left coordinate of the found image
        else:
            print("Image not found in screenshot.")
            return None
    except Exception as e:
        print(f"Error in check_by_image: {e}")
        return None

def main(json_file):
    data = load_json(json_file)
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    x = driver.execute_script("return window.screenX;")  # Output: 0
    y = driver.execute_script("return window.screenY;")  # Output: 0    
    print('Web browser position: {} {}'.format(x,y))
    for action in data.get("actions", []):
        command = action.get("command")
        args = action.get("args", {})
        
        if command == "OpenURL":
            open_url(driver, args.get("url"))
            time.sleep(3)
        elif command == "New Tab":
            new_tab(driver)
        elif command == "Close Tab":
            close_tab(driver)
        elif command == "Reload":
            reload_page(driver)
        elif command == "Go Back":
            go_back(driver)
        elif command == "Mouse Click":
            mouse_click(args.get("x"), args.get("y"))
        elif command == "Mouse Press and Hold":
            mouse_press_and_hold(args.get("x"), args.get("y"), args.get("duration", 2))
        elif command == "Mouse Move":
            mouse_move(args.get("x"), args.get("y"))
        elif command == "Mouse Scroll":
            mouse_scroll(args.get("amount"))
        elif command == "Keyboard Press":
            keyboard_press(args.get("key"))
        elif command == "Keyboard Hold":
            keyboard_hold(args.get("key"), args.get("duration", 2))
        elif command == "Keyboard Type":
            keyboard_type(args.get("text"))
        elif command == "Click Element":
            locate_and_click_element(driver, args.get("full_x_path"))
        elif command == "Check by Image":
            check_by_image(args.get("img_path"), args.get("threshold"))
        
        print(f"Done with: {command}")
        time.sleep(1)
    # time.sleep(100)
    driver.quit()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <commands.json>")
        sys.exit(1)
    main(sys.argv[1])
