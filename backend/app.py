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

def convert_js_path_to_css(js_path):
    css_selector = js_path.replace(" > ", " ").strip()
    css_selector = re.sub(r'\:nth-of-type\((\d+)\)', r':nth-child(\1)', css_selector)
    return css_selector

def locate_and_click_element(driver, js_path):
    try:
        element = driver.execute_script(f"return document.querySelector('{js_path}')")
        if element:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            driver.execute_script("arguments[0].style.border='3px solid red'", element)
            rect = driver.execute_script("return arguments[0].getBoundingClientRect();", element)
            window_x = driver.execute_script("return window.screenX;")
            window_y = driver.execute_script("return window.screenY;")

            # Get browser UI offset (tabs, search bar)
            browser_ui_offset = driver.execute_script("return window.outerHeight - window.innerHeight;")
            print(f'browser_ui_offset: {browser_ui_offset}')
            # Adjust y-coordinate to include browser UI
            x = window_x + rect['left'] + rect['width'] / 2
            y = window_y + browser_ui_offset + rect['top'] + rect['height'] / 2
            print(f"Element Position: X={x}, Y={y}")
            driver.execute_script("arguments[0].click();", element)
            return int(x), int(y)
    except Exception as e:
        print(f"Error finding or clicking element: {e}")
    return None, None

def get_browser_position(driver):
    x = driver.execute_script("return window.screenX;")  # Output: 0
    y = driver.execute_script("return window.screenY;")  # Output: 0
    return x, y

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
        elif command == "Move To Element":
            locate_and_click_element(driver, args.get("js_path"))
        print(f"Done with: {command}")
        time.sleep(1)
    driver.quit()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <commands.json>")
        sys.exit(1)
    main(sys.argv[1])
