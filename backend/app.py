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
from selenium.webdriver.chrome.options import Options
import cv2
import numpy as np
import os

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

def mouse_click():
    pyautogui.click()

def mouse_press_and_hold(x, y, duration=2):
    pyautogui.mouseDown(x, y)
    time.sleep(duration)
    pyautogui.mouseUp(x, y)

def mouse_move(x, y):
    pyautogui.moveTo(x, y)

def mouse_scroll(amount):
    pyautogui.scroll(amount)

def keyboard_press(key):
    print(key)
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

def get_next_screenshot_index():
    os.makedirs("screenshots", exist_ok=True)
    existing_files = [f for f in os.listdir("screenshots") if f.startswith("screenshot_") and f.endswith(".png")]
    indices = [int(f.split("_")[1].split(".")[0]) for f in existing_files if f.split("_")[1].split(".")[0].isdigit()]
    return max(indices, default=-1) + 1

def check_by_image(input_image_path, roi=None, threshold=0.8, debug=False, check_emergency_pause=None):
    start_time = time.time()
    while True:
        # Check for emergency pause
        if check_emergency_pause and check_emergency_pause():
            print("Emergency pause detected during image check")
            return None
            
        try:
            elapsed_time = time.time() - start_time
            if elapsed_time > 10:
                print("Image not found within 10 seconds. Exiting...")
                return None
            
            # Take a screenshot
            screenshot = pyautogui.screenshot()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Load the input image (template)
            input_image = cv2.imread(input_image_path, cv2.IMREAD_COLOR)
            if input_image is None:
                print("Error: Input image not found.")
                return None
            input_height, input_width = input_image.shape[:2]
            
            offset_x, offset_y = 0, 0
            
            # Crop the search region if ROI is provided
            if roi is not None:
                (top_left, bottom_right) = roi
                offset_x, offset_y = top_left
                screenshot = screenshot[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
                
            # Perform template matching
            result = cv2.matchTemplate(screenshot, input_image, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # If the match exceeds the threshold, process the result
            if max_val >= threshold:
                match_x, match_y = max_loc
                match_x += offset_x  # Adjust coordinates based on ROI
                match_y += offset_y
                
                middle_x = match_x + input_width // 2
                middle_y = match_y + input_height // 2
                print(f"Image found at: {match_x}, {match_y}")
                print(f"Middle point of the image: ({middle_x}, {middle_y})")
                
                # Draw a bounding box around the found image
                cv2.rectangle(screenshot, (match_x - offset_x, match_y - offset_y),
                              (match_x - offset_x + input_width, match_y - offset_y + input_height), (0, 255, 0), 2)
                
                if debug:
                    cv2.imshow("Found Image", screenshot)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                    
                screenshot_index = get_next_screenshot_index()
                screenshot_path = f"screenshots/screenshot_{screenshot_index}.png"
                cv2.imwrite(screenshot_path, screenshot)
                print(f"Saved: {screenshot_path}")
                    
                return (middle_x, middle_y)
                
            # Small delay before next check, with emergency pause check
            for _ in range(5):  # Check pause every 100ms
                time.sleep(0.1)
                if check_emergency_pause and check_emergency_pause():
                    print("Emergency pause detected during image check")
                    return None
                
        except Exception as e:
            print(f"Error in check_by_image: {e}")
                        
def check_by_image_and_move(input_image_path, threshold=0.8, roi=None, debug=False, check_emergency_pause=None):
    position = check_by_image(
        input_image_path=input_image_path, 
        threshold=threshold, 
        roi=roi, 
        debug=debug,
        check_emergency_pause=check_emergency_pause
    )
    if position is not None:
        pyautogui.moveTo(position[0], position[1])
    else:
        print("Image not found in screenshot.")

def send_hotkey(*keys):
    print(f"Sending hotkey: {keys}")
    pyautogui.hotkey(*keys)

def connect_driver():
    options = Options()
    options.debugger_address = "127.0.0.1:9222"
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def create_emergency_pause_checker(emergency_pause_flag_ref):
    """
    Creates a function that checks if emergency pause has been requested
    
    Args:
        emergency_pause_flag_ref: A reference to the emergency pause flag variable
        
    Returns:
        Function that returns True if emergency pause is requested
    """
    def check_emergency_pause():
        # Check if emergency pause has been requested
        if emergency_pause_flag_ref is None:
            return False
            
        # Handle Event objects
        if hasattr(emergency_pause_flag_ref, 'is_set'):
            return emergency_pause_flag_ref.is_set()
            
        # Handle ThreadSafeReference with 'value' attribute
        elif hasattr(emergency_pause_flag_ref, 'value'):
            return bool(emergency_pause_flag_ref.value)
            
        # Handle boolean-like objects
        else:
            return bool(emergency_pause_flag_ref)
            
    return check_emergency_pause

def safe_sleep(duration, check_emergency_pause=None):
    """Sleep with emergency pause checks"""
    if not check_emergency_pause:
        time.sleep(duration)
        return False
        
    # Split sleep into small increments to check for emergency pause
    increment = 0.1  # Check every 100ms
    iterations = int(duration / increment) + 1
    
    for _ in range(iterations):
        if check_emergency_pause():
            print("Emergency pause detected during sleep")
            return True
        # Sleep for the smaller increment or the remaining time
        time_left = max(0, duration - (_ * increment))
        sleep_time = min(increment, time_left)
        if sleep_time > 0:
            time.sleep(sleep_time)
            
    return False

def main(json_file, emergency_pause_flag=None):
    """
    Main function that executes a workflow from a JSON file
    
    Args:
        json_file: Path to the JSON workflow file
        emergency_pause_flag: Reference to a flag that indicates if emergency pause is requested
    """
    data = load_json(json_file)
    
    # Create emergency pause checker
    check_emergency_pause = None
    if emergency_pause_flag is not None:
        check_emergency_pause = create_emergency_pause_checker(emergency_pause_flag)
        print("Emergency pause functionality enabled")
    
    driver = None
    for group_name, actions in data.items():  # Iterate over all action groups
        print(f"Executing group: {group_name}")
        
        # Check for emergency pause before starting group
        if check_emergency_pause and check_emergency_pause():
            print("Emergency stop requested! Halting execution.")
            return
            
        for action in actions:
            # Check for emergency pause before each command
            if check_emergency_pause and check_emergency_pause():
                print("Emergency stop requested! Halting execution.")
                return
                
            command = action.get("command")
            args = action.get("args", {})
            print(action)
            
            try:
                if command == "OpenURL":
                    open_url(driver, args.get("url"))
                    if safe_sleep(3, check_emergency_pause):
                        return
                elif command == "New Tab":
                    new_tab(driver)
                elif command == "Close Tab":
                    close_tab(driver)
                elif command == "Reload":
                    reload_page(driver)
                elif command == "Go Back":
                    go_back(driver)
                elif command == "Mouse Click":
                    mouse_click()
                elif command == "Mouse Press and Hold":
                    # Check if we should do this operation with pause checks
                    duration = args.get("duration", 2)
                    if duration > 0.5 and check_emergency_pause:
                        pyautogui.mouseDown(args.get("x"), args.get("y"))
                        if safe_sleep(duration, check_emergency_pause):
                            pyautogui.mouseUp()  # Make sure to release
                            return
                        pyautogui.mouseUp(args.get("x"), args.get("y"))
                    else:
                        mouse_press_and_hold(args.get("x"), args.get("y"), duration)
                elif command == "Mouse Move":
                    mouse_move(args.get("x"), args.get("y"))
                elif command == "Mouse Scroll":
                    mouse_scroll(args.get("amount"))
                elif command == "Keyboard Press":
                    keyboard_press(args.get("key"))
                elif command == "Keyboard Hold":
                    # Check if we should do this operation with pause checks
                    duration = args.get("duration", 2)
                    if duration > 0.5 and check_emergency_pause:
                        pyautogui.keyDown(args.get("key"))
                        if safe_sleep(duration, check_emergency_pause):
                            pyautogui.keyUp(args.get("key"))  # Make sure to release
                            return
                        pyautogui.keyUp(args.get("key"))
                    else:
                        keyboard_hold(args.get("key"), duration)
                elif command == "Keyboard Type":
                    keyboard_type(args.get("text"))
                elif command == "Click Element":
                    locate_and_click_element(driver, args.get("full_x_path"))
                elif command == "Check by Image":
                    check_by_image(
                        input_image_path=args.get("img_path"), 
                        threshold=args.get("threshold", 0.8), 
                        roi=args.get("roi", None), 
                        debug=args.get("debug", False),
                        check_emergency_pause=check_emergency_pause
                    )
                elif command == "Check by Image And Move":
                    check_by_image_and_move(
                        input_image_path=args.get("img_path"), 
                        threshold=args.get("threshold", 0.8), 
                        roi=args.get("roi", None), 
                        debug=args.get("debug", False),
                        check_emergency_pause=check_emergency_pause
                    )
                elif command == "Send Hotkey":
                    send_hotkey(*args.get("keys"))
                elif command == "Connect Driver":
                    driver = connect_driver()
                elif command == "Pause":
                    duration = args.get("duration", 1)
                    if safe_sleep(duration, check_emergency_pause):
                        return
                
                print(f"Done with: {command}")
                
                # Small delay between commands with emergency pause check
                if safe_sleep(1, check_emergency_pause):
                    return
                    
            except Exception as e:
                print(f"Error executing command {command}: {e}")
                # Don't break execution, continue with next command
                
            # Final check after command execution
            if check_emergency_pause and check_emergency_pause():
                print("Emergency stop requested after command execution! Halting.")
                return
                
        print(f"Completed group: {group_name}")
        
    print("Workflow execution completed successfully")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <commands.json>")
        sys.exit(1)
    main(sys.argv[1])