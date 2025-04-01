import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import tempfile
import os
import sys
import importlib.util
import time
import pyautogui
import threading
import time
import keyboard
import cv2
import numpy as np
import threading
import ctypes
from threading import Event

class WorkflowBuilder:
    def __init__(self, root):
        self.test_running = False
        self.test_thread = None
        self.emergency_stop_flag = Event() 
        
        self.undo_stack = []
        self.max_undo_stack = 20
        self.text_field_original_values = {}
        
        # Define dark theme colors
        self.colors = {
            "bg": "#1e1e1e",            # Dark background
            "fg": "#e0e0e0",            # Light text
            "button_bg": "#2d2d2d",     # Dark button
            "button_fg": "#e0e0e0",     # Light button text
            "frame_bg": "#252526",      # Slightly lighter background for frames
            "accent": "#0d7377",        # Teal accent color
            "highlight": "#0e9aa7",     # Brighter teal for highlights
            "border": "#3e3e42",        # Border color
            "input_bg": "#333333",      # Input field background
            "success": "#4caf50",       # Success color
            "warning": "#ff9800",       # Warning color
            "error": "#f44336",         # Error color
            "header_bg": "#202020",     # Header background
        }
        
        self.geometries = {
            (3840, 2160): {
                'font_tiny': 10,
                'font_small': 12,
                'font_large': 16,
                'main_width': 3000,
                'main_height': 1440,
                'get_mouse_width': 500,
                'get_mouse_height': 500,
                'select_roi_width': 600,
                'select_roi_height': 350,
                'button_small_command': 5,
                'button_large_command': 10,
                'button_small_group': 8,
                'button_large_group': 15,
                'emergency_width': 300,
                'emergency_height': 100,
                'show_emergency_ui_x': 20,
                'show_emergency_ui_y': 20,
                'show_result_width': 2500,
                'show_result_height': 1000,
                'group_name_width': 30,
                'command_name_width': 25,
                'update_command_args_tiny_width': 7,
                'update_command_args_small_width': 15,
                'update_command_args_medium_width': 20,
                'update_command_args_large_width': 40,
                'button_largupdate_command_args_max_width': 100,
            },
            (1920, 1080): {
                'font_tiny': 8,
                'font_small': 10,
                'font_large': 14,
                'main_width': 1500,
                'main_height': 800,
                'get_mouse_width': 300,
                'get_mouse_height': 300,
                'select_roi_width': 300,
                'select_roi_height': 150,
                'button_small_command': 5,
                'button_large_command': 10,
                'button_small_group': 8,
                'button_large_group': 15,
                'emergency_width': 150,
                'emergency_height': 50,
                'show_emergency_ui_x': 10,
                'show_emergency_ui_y': 10,
                'show_result_width': 1300,
                'show_result_height': 600,
                'group_name_width': 30,
                'command_name_width': 25,
                'update_command_args_tiny_width': 7,
                'update_command_args_small_width': 15,
                'update_command_args_medium_width': 20,
                'update_command_args_large_width': 40,
                'button_largupdate_command_args_max_width': 100,
            },
            (2560, 1440): {},
        }
        
        self.root = root
        self.root.title("Workflow Builder - Dark Theme")
        
        # Apply dark theme to root
        self.root.configure(bg=self.colors["bg"])
        
        # Configure theme for ttk widgets
        self.configure_ttk_styles()
        self.configure_dialog_colors()
        
        # Get screen dimensions to calculate appropriate window size
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Set window size as a percentage of screen dimensions
        window_width = self.geometries[(screen_width, screen_height)]['main_width']
        window_height = self.geometries[(screen_width, screen_height)]['main_height']
        
        # Position the window in the center of the screen
        position_x = int((screen_width - window_width) / 2)
        position_y = int((screen_height - window_height) / 2)
        
        # Set window geometry
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        self.root.bind("<Control-z>", self.undo_last_action)
        self.root.bind("<Button-1>", self.clear_focus)
        self.root.bind("<Return>", self.clear_focus)
        
        self.workflow = {}
        self.groups_frames = {}
        self.backend_module = None
        
        # Try to import the backend module
        self.load_backend_module()
        
        # Configure the root window to resize properly
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Main frame with scrollbar
        self.main_frame = tk.Frame(root, bg=self.colors["bg"])
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure the main frame to resize properly
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)  # Row 1 is for the canvas
        
        # Button frame
        self.button_frame = tk.Frame(self.main_frame, bg=self.colors["header_bg"])
        self.button_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        # Calculate button sizes based on window width
        button_width = max(10, int((window_width * 0.12) / 10))  # Scale button width
        
        # Add buttons
        buttons = [
            ("Add Group", self.add_group),
            ("Save Workflow", self.save_workflow),
            ("Load Workflow", self.load_workflow),
            ("Test Workflow", self.test_workflow),
            ("Get Mouse Position", self.get_mouse_position),
            ("Select ROI", self.select_roi_from_image),
            ("Add Chrome Group", self.add_chrome_group),
        ]
        
        for i, (text, command) in enumerate(buttons):
            tk.Button(self.button_frame, text=text, command=command, width=button_width,
                     bg=self.colors["button_bg"], fg=self.colors["button_fg"],
                     activebackground=self.colors["highlight"], 
                     activeforeground=self.colors["fg"],
                     font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                     relief=tk.FLAT, bd=0).grid(
                row=0, column=i, padx=5, pady=5, sticky="ew"
            )
            self.button_frame.grid_columnconfigure(i, weight=1)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(self.main_frame, bg=self.colors["bg"], 
                              highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", 
                                     command=self.canvas.yview,
                                     bg=self.colors["button_bg"], 
                                     troughcolor=self.colors["bg"])
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Frame inside canvas for groups
        self.groups_container = tk.Frame(self.canvas, bg=self.colors["bg"])
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.groups_container, anchor="nw")
        
        # Make the groups container expandable
        self.groups_container.grid_columnconfigure(0, weight=1)
        
        # Configure canvas scrolling
        self.groups_container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        # For Linux and Mac (may need further adjustment for Mac)
        self.canvas.bind_all("<Button-4>", lambda e: self.on_mousewheel_linux(e, -1))
        self.canvas.bind_all("<Button-5>", lambda e: self.on_mousewheel_linux(e, 1))
        
    def create_emergency_stop_ui(self):
        """Create a small transparent emergency stop window with just the button"""
        # Create a floating top-level window for the emergency button
        self.emergency_window = tk.Toplevel(self.root)
        self.emergency_window.title("")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = self.geometries[(screen_width, screen_height)]['emergency_width']
        window_height = self.geometries[(screen_width, screen_height)]['emergency_height']
        
        # Set the window size
        self.emergency_window.geometry(f"{window_width}x{window_height}")

        self.emergency_window.attributes("-alpha", 0.4)  # 90% opacity
        self.emergency_window.attributes("-topmost", True)  # Stay on top
        self.emergency_window.overrideredirect(True)  # Remove window decorations
        
        # Set background to error color
        self.emergency_window.configure(bg=self.colors["error"])
        
        # Add a thin border frame
        frame = tk.Frame(
            self.emergency_window,
            bg="white",
            bd=1
        )
        frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Add just the emergency stop button (filling the whole window)
        stop_button = tk.Button(
            frame,
            text="EMERGENCY STOP",
            font=("Arial", self.geometries[(screen_width, screen_height)]['font_small'], "bold"),
            command=self.trigger_emergency_pause,
            bg="#ff0000",
            fg="white",
            activebackground="#ff6b6b",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2
        )
        stop_button.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        # Add dragging capability since we removed the title bar
        self.add_window_drag_capability(self.emergency_window)
        
        # Hide window initially
        self.emergency_window.withdraw()
        
        return self.emergency_window

    def add_window_drag_capability(self, window):
        """Add the ability to drag a window without a title bar"""
        def start_drag(event):
            window.x = event.x
            window.y = event.y

        def drag(event):
            deltax = event.x - window.x
            deltay = event.y - window.y
            x = window.winfo_x() + deltax
            y = window.winfo_y() + deltay
            window.geometry(f"+{x}+{y}")

        window.bind("<ButtonPress-1>", start_drag)
        window.bind("<B1-Motion>", drag)
    
    def show_emergency_ui(self):
        """Show the emergency stop UI in the bottom left of the screen"""
        if hasattr(self, 'emergency_window'):
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Set window size as a percentage of screen dimensions
            pos_x = self.geometries[(screen_width, screen_height)]['show_emergency_ui_x']
            pos_y = self.geometries[(screen_width, screen_height)]['show_emergency_ui_y']
            
            # Set the position
            self.emergency_window.geometry(f"+{pos_x}+{pos_y}")
            
            # Show window
            self.emergency_window.deiconify()
        else:
            # Create if it doesn't exist
            self.create_emergency_stop_ui()
            # Reposition it (as create_emergency_stop_ui may position it elsewhere)
            self.show_emergency_ui()  # Recursive call to apply positioning
    
    def hide_emergency_ui(self):
        """Hide the emergency stop UI"""
        if hasattr(self, 'emergency_window'):
            # Reset any states if needed
            for widget in self.emergency_window.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Button):
                            # Reset button text and state
                            child.config(
                                text="EMERGENCY STOP",
                                state=tk.NORMAL,
                                bg="#ff0000",
                                fg="white"
                            )
            
            # Hide the window
            self.emergency_window.withdraw()
    
    def trigger_emergency_pause(self):
        """Handler for emergency pause button click"""
        # Check if we're running and not already stopping
        if not self.test_running or hasattr(self, 'stopping') and self.stopping:
            return
            
        # Set flag to prevent multiple stop attempts
        self.stopping = True
        print('trigger_emergency_pause')
        
        # Set the emergency flag
        self.emergency_stop_flag.set()
        
        # Update the emergency window UI to show stopping
        if hasattr(self, 'emergency_window'):
            for widget in self.emergency_window.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Button):
                            child.config(text="STOPPING...", state=tk.DISABLED)
                elif isinstance(widget, tk.Button):
                    widget.config(text="STOPPING...", state=tk.DISABLED)
                elif isinstance(widget, tk.Label):
                    widget.config(text="STOPPING WORKFLOW...")
        
        # Use a safer approach for thread management
        # Schedule the termination check to run after a short delay
        self.root.after(500, self.force_terminate_if_needed)

    def force_terminate_if_needed(self):
        """Force terminate the thread if it's still running after emergency stop"""
        # If thread is still alive, try to force terminate it
        if self.test_thread and self.test_thread.is_alive():
            try:
                # Force terminate the thread on Windows
                if hasattr(self.test_thread, "_thread_id"):
                    thread_id = self.test_thread._thread_id
                    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(thread_id),
                        ctypes.py_object(KeyboardInterrupt)
                    )
                    if res > 1:
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(
                            thread_id, 
                            ctypes.c_long(0)
                        )
                print("Forced thread termination")
            except Exception as e:
                print(f"Error during forced termination: {e}")
            
            # Wait a bit more and check again
            self.root.after(500, self.check_if_terminated)
        else:
            # Thread already terminated, make sure UI gets updated
            self.check_if_terminated()

    def check_if_terminated(self):
        """Check if the thread is terminated and update UI if needed"""
        if not self.test_thread or not self.test_thread.is_alive():
            # Thread is done, make sure UI is updated
            if self.test_running:  # If finish_test hasn't been called yet
                # Force finish with emergency stop message
                self.finish_emergency()
        else:
            # Thread still alive, try one more force termination
            try:
                if hasattr(self.test_thread, "_thread_id"):
                    thread_id = self.test_thread._thread_id
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(thread_id),
                        ctypes.py_object(SystemExit)
                    )
                print("Final termination attempt")
            except:
                pass
            
            # Final check and forced finish
            self.root.after(500, self.finish_emergency)

    def finish_emergency(self):
        """Forcibly finish a test that was emergency stopped"""
        # Directly call finish_test with predetermined values
        self.finish_test(
            success=False,
            stdout="Emergency stop forced test termination.",
            stderr="The workflow was forcibly stopped and did not complete normally.",
            test_type="interrupted workflow"
        )
     
    def configure_ttk_styles(self):
        """Configure ttk styles for dark theme"""
        style = ttk.Style()
        
        # Configure TCombobox
        style.configure('TCombobox', 
                    fieldbackground=self.colors["input_bg"],
                    background=self.colors["input_bg"],
                    foreground=self.colors["fg"],
                    arrowcolor=self.colors["fg"],
                    bordercolor=self.colors["border"])
        
        # Configure TButton
        style.configure('TButton',
                    background=self.colors["button_bg"],
                    foreground=self.colors["fg"],
                    bordercolor=self.colors["border"],
                    relief=tk.FLAT)
        
        # Configure TEntry
        style.configure('TEntry',
                    fieldbackground=self.colors["input_bg"],
                    foreground=self.colors["fg"],
                    bordercolor=self.colors["border"])
        
        # Configure TNotebook
        style.configure('TNotebook',
                    background=self.colors["bg"],
                    bordercolor=self.colors["border"])
        
        # Configure TNotebook.Tab - this affects all tabs
        style.configure('TNotebook.Tab',
                    background=self.colors["button_bg"],
                    foreground="#999999",
                    font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                    padding=[10, 2])
        
        # Configure selected tab appearance
        style.map('TNotebook.Tab',
                background=[('selected', self.colors["accent"])],
                foreground=[('selected', "#000000")])  # Bright white text for selected tab
        
        # Configure TScrollbar
        style.configure('TScrollbar',
                    background=self.colors["button_bg"],
                    troughcolor=self.colors["bg"],
                    bordercolor=self.colors["border"],
                    arrowcolor=self.colors["fg"])
        
    def configure_dialog_colors(self):
        """Configure file dialogs and message boxes to use dark theme"""
        # This method should be called in the __init__ method
        
        # For file dialogs, we can't directly style them in Tkinter
        # However, we can set the background color of the root window
        # which might affect system dialogs on some platforms
        self.root.option_add('*Dialog.msg.background', self.colors["bg"])
        self.root.option_add('*Dialog.msg.foreground', self.colors["fg"])
        
        # For message boxes
        font_size = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small']
        self.root.option_add('*Dialog.msg.font',f'Arial {font_size}')
        
        # Set button colors
        self.root.option_add('*Dialog.button.background', self.colors["button_bg"])
        self.root.option_add('*Dialog.button.foreground', self.colors["button_fg"])
        self.root.option_add('*Dialog.button.activeBackground', self.colors["highlight"])
        self.root.option_add('*Dialog.button.activeForeground', self.colors["fg"])

    def on_mousewheel_linux(self, event, direction):
        # Scroll canvas with mouse wheel (Linux/Mac)
        self.canvas.yview_scroll(direction, "units")
    
    def on_frame_configure(self, event):
        # Update the scrollregion when the inner frame changes size
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        # Update the width of the window to match the canvas
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def on_mousewheel(self, event):
        # Scroll canvas with mouse wheel
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def update_group_name(self, old_name, new_name):
        if old_name == new_name:
            return
            
        if new_name in self.workflow:
            messagebox.showerror("Error", "Group name already exists!")
            # Reset the name in the UI
            for child in self.groups_frames[old_name].winfo_children():
                if isinstance(child, tk.Frame):  # Header frame
                    for widget in child.winfo_children():
                        if isinstance(widget, tk.Entry):
                            widget.delete(0, tk.END)
                            widget.insert(0, old_name)
                            break
            return
        
        # Update workflow dict
        self.workflow[new_name] = self.workflow[old_name]
        del self.workflow[old_name]
        
        # Update frames dict
        self.groups_frames[new_name] = self.groups_frames[old_name]
        del self.groups_frames[old_name]
        
        # Update the label frame text if needed
        if hasattr(tk, 'LabelFrame') and isinstance(self.groups_frames[new_name], tk.LabelFrame):
            self.groups_frames[new_name].config(text=new_name)
        
        # Update the command bindings for the group
        for child in self.groups_frames[new_name].winfo_children():
            if isinstance(child, tk.Frame) and not hasattr(child, 'commands_frame'):  # Header frame
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Button) and widget['text'] == "Add Command":
                        widget.config(command=lambda: self.add_command(new_name))
                    elif isinstance(widget, tk.Button) and widget['text'] == "Test Group":
                        widget.config(command=lambda: self.test_workflow(group_name=new_name))
                    elif isinstance(widget, tk.Button) and widget['text'] == "Remove Group":
                        widget.config(command=lambda: self.remove_group(new_name))
  
    def browse_image(self, entry_widget):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def update_workflow_command(self, group_name, command_frame):
        # Get command type from the stored command_var
        if hasattr(command_frame, 'command_var'):
            command_type = command_frame.command_var.get()
        else:
            # Fallback method - try to find an OptionMenu in the children
            for widget in command_frame.winfo_children():
                if isinstance(widget, tk.OptionMenu):
                    command_type = widget.cget("textvariable")
                    if isinstance(command_type, str):
                        # It's a string reference to a Tkinter variable
                        command_type = self.root.nametowidget(command_type).get()
                        break
                    else:
                        # It's already a StringVar
                        command_type = command_type.get()
                        break
            else:
                # No command type found
                return

        # Get args from widgets
        args = {}
        for key, widget in getattr(command_frame, 'arg_widgets', []):
            value = widget.get()
            
            # Skip empty ROI values for image commands
            if key == 'roi' and value.strip() == '' and command_type in ["Check by Image", "Check by Image And Move"]:
                continue
                
            if ',' in value and key == 'keys':  # Handle comma-separated values
                args[key] = [v.strip() for v in value.split(',')]
            elif key in ['x', 'y']:  # Convert coordinates to integers
                try:
                    args[key] = int(value) if value else 0
                except ValueError:
                    args[key] = 0
            elif key == 'duration':
                try:
                    args[key] = float(value) if value else 1.0
                except ValueError:
                    args[key] = 1.0
            else:
                # Don't add empty values to keep JSON clean
                if value.strip():
                    args[key] = value
        
        # Create command data
        command_data = {
            'command': command_type,
            'args': args
        }
        
        # Find index of command in group
        group_commands = self.groups_frames[group_name].commands_frame.winfo_children()
        index = group_commands.index(command_frame)
        
        # Update or add to workflow
        if 0 <= index < len(self.workflow[group_name]):
            self.workflow[group_name][index] = command_data
        else:
            self.workflow[group_name].append(command_data)
    
    def save_workflow(self):
        # Update all commands in workflow before saving
        for group_name, group_frame in self.groups_frames.items():
            commands_frame = group_frame.commands_frame
            for i, command_frame in enumerate(commands_frame.winfo_children()):
                self.update_workflow_command(group_name, command_frame)
                    
                # Special handling for values that need conversion
                if i < len(self.workflow[group_name]):
                    command_data = self.workflow[group_name][i]
                    if 'args' in command_data:
                        # Convert ROI values from string to nested list
                        if 'roi' in command_data['args']:
                            roi_value = command_data['args']['roi']
                            # If roi is a string, convert it to a nested list format
                            if isinstance(roi_value, str):
                                try:
                                    # Parse the string representation
                                    # Handle both formats: "[x1, y1], [x2, y2]" or "x1, y1, x2, y2"
                                    if '[' in roi_value:
                                        # Format: "[x1, y1], [x2, y2]"
                                        parts = roi_value.replace('[', '').replace(']', '').split(',')
                                        coords = [int(p.strip()) for p in parts]
                                        if len(coords) == 4:  # Ensure we have 4 coordinates
                                            command_data['args']['roi'] = [[coords[0], coords[1]], [coords[2], coords[3]]]
                                    else:
                                        # Format: "x1, y1, x2, y2"
                                        coords = [int(p.strip()) for p in roi_value.split(',')]
                                        if len(coords) == 4:  # Ensure we have 4 coordinates
                                            command_data['args']['roi'] = [[coords[0], coords[1]], [coords[2], coords[3]]]
                                except (ValueError, IndexError):
                                    # If parsing fails, keep original format
                                    pass
                            
                        # Convert threshold from string to float
                        if 'threshold' in command_data['args']:
                            threshold_value = command_data['args']['threshold']
                            if isinstance(threshold_value, str):
                                try:
                                    # Convert to float first (since threshold is often a decimal like 0.8)
                                    float_value = float(threshold_value)
                                    command_data['args']['threshold'] = float_value
                                except ValueError:
                                    # If conversion fails, keep original format
                                    pass
        
        # Ask for filename
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        # Save to file
        try:
            with open(filename, 'w') as f:
                json.dump(self.workflow, f, indent=2)
            messagebox.showinfo("Success", f"Workflow saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save workflow: {e}")
            
    def load_workflow(self):
        # Ask for filename
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        # Load from file
        try:
            with open(filename, 'r') as f:
                loaded_data = json.load(f)
            
            # Validate the loaded data structure
            if not isinstance(loaded_data, dict):
                raise ValueError("Invalid workflow format: Root must be a dictionary")
                
            # Create a valid workflow structure
            self.workflow = {}
            for group_name, commands in loaded_data.items():
                # Skip invalid group names
                if not isinstance(group_name, str):
                    continue
                    
                # Ensure commands is a list
                if not isinstance(commands, list):
                    self.workflow[group_name] = []
                    continue
                    
                # Add valid commands
                self.workflow[group_name] = []
                for cmd in commands:
                    if isinstance(cmd, dict) and 'command' in cmd:
                        if 'args' not in cmd or not isinstance(cmd['args'], dict):
                            cmd['args'] = {}
                        self.workflow[group_name].append(cmd)
            
            # Clear existing groups
            for frame in self.groups_frames.values():
                frame.destroy()
            self.groups_frames = {}
            
            # Add loaded groups and commands
            for group_name, commands in self.workflow.items():
                group_frame = self.add_group(group_name, is_loading=True)
                for command_data in commands:
                    # Make sure command_data has 'args' key, even if empty
                    if 'args' not in command_data:
                        command_data['args'] = {}
                    # Ensure command_data has valid structure
                    if not isinstance(command_data, dict) or 'command' not in command_data:
                        command_data = {'command': '', 'args': {}}
                    self.add_command(group_name, command_data)            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load workflow: {e}")
    
    def get_command_index(self, group_name, command_frame):
        """Get the index of a command frame within its group"""
        if group_name not in self.groups_frames:
            return -1
            
        group_commands = self.groups_frames[group_name].commands_frame.winfo_children()
        return group_commands.index(command_frame) if command_frame in group_commands else -1
    
    def test_workflow(self, group_name=None, command_index=None):
        """
        Modified test_workflow method with threading and emergency pause support
        """
        # Make sure the flag is cleared before testing
        self.emergency_stop_flag.clear()
        
        if hasattr(self, 'stopping'):
            delattr(self, 'stopping')
        
        # Update all commands in workflow before testing
        for g_name, group_frame in self.groups_frames.items():
            commands_frame = group_frame.commands_frame
            for i, command_frame in enumerate(commands_frame.winfo_children()):
                self.update_workflow_command(g_name, command_frame)
                    
                # Special handling for values that need conversion
                if i < len(self.workflow[g_name]):
                    command_data = self.workflow[g_name][i]
                    if 'args' in command_data:
                        # Convert ROI values from string to nested list
                        if 'roi' in command_data['args']:
                            roi_value = command_data['args']['roi']
                            # If roi is a string, convert it to a nested list format
                            if isinstance(roi_value, str):
                                try:
                                    # Parse the string representation
                                    # Handle both formats: "[x1, y1], [x2, y2]" or "x1, y1, x2, y2"
                                    if '[' in roi_value:
                                        # Format: "[x1, y1], [x2, y2]"
                                        parts = roi_value.replace('[', '').replace(']', '').split(',')
                                        coords = [int(p.strip()) for p in parts]
                                        if len(coords) == 4:  # Ensure we have 4 coordinates
                                            command_data['args']['roi'] = [[coords[0], coords[1]], [coords[2], coords[3]]]
                                    else:
                                        # Format: "x1, y1, x2, y2"
                                        coords = [int(p.strip()) for p in roi_value.split(',')]
                                        if len(coords) == 4:  # Ensure we have 4 coordinates
                                            command_data['args']['roi'] = [[coords[0], coords[1]], [coords[2], coords[3]]]
                                except (ValueError, IndexError):
                                    # If parsing fails, keep original format
                                    pass
                            
                        # Convert threshold from string to float
                        if 'threshold' in command_data['args']:
                            threshold_value = command_data['args']['threshold']
                            if isinstance(threshold_value, str):
                                try:
                                    # Convert to float first (since threshold is often a decimal like 0.8)
                                    float_value = float(threshold_value)
                                    command_data['args']['threshold'] = float_value
                                except ValueError:
                                    # If conversion fails, keep original format
                                    pass
        
        try:
            # Show the emergency UI
            self.show_emergency_ui()
            
            # Create a test workflow based on what's being tested
            test_workflow = {}
            
            if group_name is not None and group_name in self.workflow:
                if command_index is not None and 0 <= command_index < len(self.workflow[group_name]):
                    # Test a single command
                    test_workflow = {group_name: [self.workflow[group_name][command_index]]}
                    test_type = f"command {command_index+1} in group '{group_name}'"
                else:
                    # Test an entire group
                    test_workflow = {group_name: self.workflow[group_name]}
                    test_type = f"group '{group_name}'"
            else:
                # Test the entire workflow
                test_workflow = self.workflow
                test_type = "entire workflow"
                        
            # Create temporary file for the workflow
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp:
                temp_filename = temp.name
                temp.write(json.dumps(test_workflow).encode())
            
            # Create a log capture class
            class LogCapture:
                def __init__(self):
                    self.logs = []
                    
                def write(self, text):
                    self.logs.append(text)
                    
                def flush(self):
                    pass
                    
                def get_logs(self):
                    return "".join(self.logs)
            
            # Create a wrapper function to run the test in a thread
            def run_test_thread():
                # Store thread ID for emergency termination
                if not hasattr(threading.current_thread(), "_thread_id"):
                    for thread_id, thread in threading._active.items():
                        if thread is threading.current_thread():
                            threading.current_thread()._thread_id = thread_id
                            break
                
                success = False
                error_msg = "Interrupted by emergency stop"
                
                # Redirect stdout and stderr to capture logs
                stdout_capture = LogCapture()
                stderr_capture = LogCapture()
                
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture
                try:
                    # Call the backend module with our temp file and emergency flag
                    self.backend_module(temp_filename, self.emergency_stop_flag)
                    success = True
                    error_msg = ""
                except Exception as e:
                    success = False
                    error_msg = str(e)
                finally:
                    # Restore stdout and stderr
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
                    # Clean up the temporary file
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                    
                    # Get captured logs
                    stdout_logs = stdout_capture.get_logs()
                    stderr_logs = stderr_capture.get_logs()
                    
                    # Update UI from main thread
                    self.root.after(100, lambda: self.finish_test(
                        success=success,
                        stdout=stdout_logs,
                        stderr=stderr_logs if stderr_logs else (error_msg if error_msg else "Unknown error"),
                        test_type=test_type
                    ))
            
            # Indicate that a test is running
            self.test_running = True
            
            # Create and start the test thread
            self.test_thread = threading.Thread(target=run_test_thread, daemon=True)
            self.test_thread.start()
                
        except Exception as e:
            # Hide emergency UI on error
            self.hide_emergency_ui()
            messagebox.showerror("Error", f"Failed to test workflow: {e}")
            # Reset state
            self.test_running = False
    
    def finish_test(self, success, stdout, stderr, test_type):
        """Called when test thread completes to update UI"""
        # Reset test state
        self.test_running = False
        self.emergency_stop_flag.clear()
        
        # Clear the stopping flags if they exist
        if hasattr(self, 'stopping'):
            delattr(self, 'stopping')
        if hasattr(self, 'stop_start_time'):
            delattr(self, 'stop_start_time')
        
        # Hide the emergency UI
        self.hide_emergency_ui()
        
        # Show results
        self.show_test_results(
            success=success,
            stdout=stdout,
            stderr=stderr,
            test_type=test_type
        )
    
    def show_test_results(self, success, stdout, stderr, test_type):
        """Show test results in a scrollable window"""
        result_window = tk.Toplevel(self.root)
        result_window.title(f"Test Results - {test_type}")
        
        # Apply dark theme to the window
        result_window.configure(bg=self.colors["bg"])
        
        # Size the result window relative to the main window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set window size as a percentage of screen dimensions
        result_window_width = self.geometries[(screen_width, screen_height)]['show_result_width']
        result_window_height = self.geometries[(screen_width, screen_height)]['show_result_height']
        
        # Position the result window centered relative to the main window
        main_window_x = self.root.winfo_x()
        main_window_y = self.root.winfo_y()
        result_window_x = main_window_x + int((screen_width - result_window_width) / 2)
        result_window_y = main_window_y + int((screen_height - result_window_height) / 2)
        
        result_window.geometry(f"{result_window_width}x{result_window_height}+{result_window_x}+{result_window_y}")
        
        # Configure grid layout
        result_window.grid_columnconfigure(0, weight=1)
        result_window.grid_rowconfigure(1, weight=1)  # Row 1 for notebook (main content)
        
        # Status label
        status_frame = tk.Frame(result_window, bg=self.colors["bg"])
        status_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        status_frame.grid_columnconfigure(0, weight=1)
        
        status_label = tk.Label(
            status_frame,
            text=f"Test {'SUCCEEDED' if success else 'FAILED'}",
            fg="green" if success else self.colors["error"],
            bg=self.colors["bg"],
            font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], "bold")
        )
        status_label.grid(row=0, column=0, sticky="w")
        
        # Notebook for stdout/stderr
        notebook = ttk.Notebook(result_window)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Stdout tab
        stdout_frame = tk.Frame(notebook, bg=self.colors["frame_bg"])
        notebook.add(stdout_frame, text="Output")
        
        # Configure stdout frame to expand
        stdout_frame.grid_columnconfigure(0, weight=1)
        stdout_frame.grid_rowconfigure(0, weight=1)
        
        stdout_scrollbar = tk.Scrollbar(stdout_frame, bg=self.colors["button_bg"], 
                                    troughcolor=self.colors["bg"])
        stdout_scrollbar.grid(row=0, column=1, sticky="ns")
        
        stdout_text = tk.Text(stdout_frame, wrap=tk.WORD, yscrollcommand=stdout_scrollbar.set, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large'], 'normal'),
                        bg=self.colors["input_bg"], fg=self.colors["fg"],
                        insertbackground=self.colors["fg"])
        stdout_text.grid(row=0, column=0, sticky="nsew")
        stdout_scrollbar.config(command=stdout_text.yview)
        
        stdout_text.insert(tk.END, stdout)
        stdout_text.config(state=tk.DISABLED)
        
        # Stderr tab (only if there are errors)
        if stderr:
            stderr_frame = tk.Frame(notebook, bg=self.colors["frame_bg"])
            notebook.add(stderr_frame, text="Errors")
            
            # Configure stderr frame to expand
            stderr_frame.grid_columnconfigure(0, weight=1)
            stderr_frame.grid_rowconfigure(0, weight=1)
            
            stderr_scrollbar = tk.Scrollbar(stderr_frame, bg=self.colors["button_bg"], 
                                        troughcolor=self.colors["bg"])
            stderr_scrollbar.grid(row=0, column=1, sticky="ns")
            
            stderr_text = tk.Text(stderr_frame, wrap=tk.WORD, yscrollcommand=stderr_scrollbar.set, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large'], 'normal'),
                            bg=self.colors["input_bg"], fg=self.colors["error"],
                            insertbackground=self.colors["fg"])
            stderr_text.grid(row=0, column=0, sticky="nsew")
            stderr_scrollbar.config(command=stderr_text.yview)
            
            stderr_text.insert(tk.END, stderr)
            stderr_text.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(result_window, text="Close", command=result_window.destroy, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
            bg=self.colors["button_bg"], fg=self.colors["button_fg"],
            activebackground=self.colors["highlight"], 
            activeforeground=self.colors["fg"],
            relief=tk.FLAT, bd=0).grid(row=2, column=0, pady=10)
     
    def load_backend_module(self):
        from backend.app import main
        self.backend_module = main
    
    def get_mouse_position(self):
        """
        Open a window that tracks and displays the current mouse position
        Uses pyautogui to get the mouse coordinates
        Stops when any key is pressed
        """
        try:
            position_window = tk.Toplevel(self.root)
            position_window.title("Mouse Position Tracker")
            screen_width = position_window.winfo_screenwidth()
            screen_height = position_window.winfo_screenheight()
            window_width = self.geometries[(screen_width, screen_height)]['get_mouse_width']
            window_height = self.geometries[(screen_width, screen_height)]['get_mouse_height']
        
            position_window.geometry(f"{window_width}x{window_height}")
            position_window.resizable(True, True)
            position_window.configure(bg=self.colors["bg"])
            coordinates_var = tk.StringVar(value="Move your mouse...")
            coordinates_label = tk.Label(
                position_window, 
                textvariable=coordinates_var,
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large']),
                height=2,
                bg=self.colors["bg"],
                fg=self.colors["fg"]
            )
            coordinates_label.pack(pady=25)
            instructions = tk.Label(
                position_window,
                text="Press ANY KEY to capture the current position",
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large']),
                wraplength=380,
                bg=self.colors["bg"],
                fg=self.colors["fg"]
            )
            instructions.pack(pady=10)
            status_var = tk.StringVar(value="Tracking mouse...")
            status_label = tk.Label(
                position_window,
                textvariable=status_var,
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large']),
                fg=self.colors["accent"],
                bg=self.colors["bg"],
                wraplength=380
            )
            status_label.pack(pady=15)
            last_position = [0, 0]
            tracking = True
            def track_position():
                while tracking:
                    try:
                        pos = pyautogui.position()
                        last_position[0], last_position[1] = pos.x, pos.y
                        coordinates_var.set(f"X: {pos.x}, Y: {pos.y}")
                        time.sleep(0.05)  # Update 20 times per second
                    except Exception as e:
                        coordinates_var.set(f"Error: {e}")
                        break
            def on_key_press(event):
                nonlocal tracking
                if tracking:
                    tracking = False
                    
                    # Copy to clipboard
                    position_window.clipboard_clear()
                    position_window.clipboard_append(f"{last_position[0]}, {last_position[1]}")
                    
                    # Update status
                    status_var.set(f"Position copied to clipboard! ({last_position[0]}, {last_position[1]})")
                    
                    # Change color to indicate success
                    status_label.config(fg=self.colors["success"])
                    
                    # Show the re-capture button
                    recapture_button.pack(pady=10)
            
            # Function to restart tracking
            def restart_tracking():
                nonlocal tracking
                if not tracking:
                    # Reset status
                    status_var.set("Tracking mouse...")
                    status_label.config(fg=self.colors["accent"])
                    
                    # Hide recapture button
                    recapture_button.pack_forget()
                    
                    # Start tracking again
                    tracking = True
                    tracking_thread = threading.Thread(target=track_position, daemon=True)
                    tracking_thread.start()

                    position_window.focus_force()
            
            recapture_button = tk.Button(
                position_window,
                text="Capture Again",
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small']),
                bg=self.colors["button_bg"],
                fg=self.colors["button_fg"],
                activebackground=self.colors["highlight"],
                activeforeground=self.colors["fg"],
                padx=10,
                relief=tk.FLAT,
                bd=0,
                command=restart_tracking
            )

            tracking_thread = threading.Thread(target=track_position, daemon=True)
            tracking_thread.start()
            
            position_window.bind("<KeyPress>", on_key_press)

            position_window.focus_force()

            def global_key_handler(e):
                if tracking:
                    on_key_press(None)
            keyboard.hook(global_key_handler)

            def on_window_close():
                nonlocal tracking
                tracking = False
                keyboard.unhook_all()
                position_window.destroy()
            
            position_window.protocol("WM_DELETE_WINDOW", on_window_close)
            
        except ImportError as e:
            if "pyautogui" in str(e):
                messagebox.showerror("Error", "PyAutoGUI is not installed. Please install it using: pip install pyautogui")
            elif "keyboard" in str(e):
                messagebox.showerror("Error", "Keyboard module is not installed. Please install it using: pip install keyboard")
            else:
                messagebox.showerror("Error", f"Missing dependency: {e}. Please install required packages.")
    
    def select_roi_from_image(self):
        """
        Allow the user to select a region of interest (ROI) from an image file.
        Returns the coordinates of the selected region using the provided select_roi function.
        """
        try:
            # First, let the user select an image file
            file_path = filedialog.askopenfilename(
                title="Select Image File",
                filetypes=[
                    ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff"),
                    ("All files", "*.*")
                ]
            )
            
            if not file_path:
                return  # User canceled file selection
            
            # Define the select_roi function as provided
            def select_roi(image_path=None, image=None):
                # Use nonlocal variables instead of global to avoid global namespace pollution
                roi = None
                selecting = False
                start_point = [0, 0]
                end_point = [0, 0]
                
                if image is None and image_path is None:
                    print("Either image_path or image should be provided")
                    return
                
                def mouse_callback(event, x, y, flags, param):
                    nonlocal selecting, start_point, end_point, roi
                    
                    if event == cv2.EVENT_LBUTTONDOWN:
                        selecting = True
                        start_point = [x, y]
                    elif event == cv2.EVENT_MOUSEMOVE and selecting:
                        end_point = [x, y]
                    elif event == cv2.EVENT_LBUTTONUP:
                        selecting = False
                        end_point = [x, y]
                        roi = [start_point, end_point]
                
                if image_path is not None:
                    image = cv2.imread(image_path)
                
                clone = image.copy()
                cv2.namedWindow("Select Region")
                cv2.setMouseCallback("Select Region", mouse_callback)
                
                while True:
                    temp_image = clone.copy()
                    if selecting or roi is not None:
                        cv2.rectangle(temp_image, tuple(start_point), tuple(end_point), (0, 255, 0), 2)
                    cv2.imshow("Select Region", temp_image)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 13:  # Enter key to confirm selection
                        break
                
                cv2.destroyAllWindows()
                return roi
            
            # Call the select_roi function with the file path
            selected_roi = select_roi(image_path=file_path)
            
            if selected_roi is None:
                return None
            
            # Create a result window to display the selection
            result_window = tk.Toplevel(self.root)
            result_window.title("ROI Selection Result")
            screen_width = result_window.winfo_screenwidth()
            screen_height = result_window.winfo_screenheight()

            window_width = self.geometries[(screen_width, screen_height)]['select_roi_width']
            window_height = self.geometries[(screen_width, screen_height)]['select_roi_height']

            # Set window geometry
            result_window.geometry(f"{window_width}x{window_height}")
            
            # Apply dark theme to the window
            result_window.configure(bg=self.colors["bg"])
            
            # Show the ROI coordinates
            tk.Label(
                result_window, 
                text="Selected Region of Interest (ROI):", 
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large'], "bold"),
                bg=self.colors["bg"],
                fg=self.colors["fg"]
            ).pack(pady=10)
            
            roi_text = str(selected_roi)[1:-1]
            tk.Label(
                result_window,
                text=roi_text,
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large']),
                bg=self.colors["bg"],
                fg=self.colors["highlight"]
            ).pack(pady=5)
            
            # Image details
            image = cv2.imread(file_path)
            height, width = image.shape[:2]
            image_info = f"Image: {os.path.basename(file_path)}\nDimensions: {width} x {height}"
            tk.Label(
                result_window,
                text=image_info,
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large']),
                justify=tk.LEFT,
                bg=self.colors["bg"],
                fg=self.colors["fg"]
            ).pack(pady=5, padx=20, anchor=tk.W)
            
            # Add a copy button
            def copy_roi():
                result_window.clipboard_clear()
                result_window.clipboard_append(roi_text)
                copy_button.config(text="Copied!")
            
            copy_button = tk.Button(
                result_window,
                text="Copy ROI to Clipboard",
                command=copy_roi,
                font=("Arial", self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_large']),
                bg=self.colors["button_bg"],
                fg=self.colors["button_fg"],
                activebackground=self.colors["highlight"],
                activeforeground=self.colors["fg"],
                relief=tk.FLAT,
                bd=0
            )
            copy_button.pack(pady=10)
            
            return selected_roi
            
        except ImportError as e:
            if "cv2" in str(e):
                messagebox.showerror("Error", "OpenCV is not installed. Please install it using: pip install opencv-python")
            else:
                messagebox.showerror("Error", f"Missing dependency: {e}. Please install required packages.")
            return None
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            return None
    
    def remove_group(self, group_name):
        # Record for undo
        if group_name in self.workflow:
            self.undo_stack.append({
                'type': 'remove_group',
                'group_name': group_name,
                'group_data': self.workflow[group_name].copy()
            })
            # Limit undo stack size
            if len(self.undo_stack) > self.max_undo_stack:
                self.undo_stack.pop(0)
                
        # Remove from workflow
        if group_name in self.workflow:
            del self.workflow[group_name]
        
        # Remove from UI
        if group_name in self.groups_frames:
            self.groups_frames[group_name].destroy()
            del self.groups_frames[group_name]
    
    def remove_command(self, group_name, command_frame):
        if group_name not in self.workflow:
            return
        
        # Find index of command in group
        group_commands = self.groups_frames[group_name].commands_frame.winfo_children()
        index = group_commands.index(command_frame)
        
        # Record for undo
        if 0 <= index < len(self.workflow[group_name]):
            self.undo_stack.append({
                'type': 'remove_command',
                'group_name': group_name,
                'command_data': self.workflow[group_name][index].copy(),
                'command_index': index
            })
            # Limit undo stack size
            if len(self.undo_stack) > self.max_undo_stack:
                self.undo_stack.pop(0)
            
            # Remove from workflow data
            self.workflow[group_name].pop(index)
        
        # Remove from UI
        command_frame.destroy()
    
    def setup_text_field_tracking(self, entry_widget, field_id):
        """Set up tracking for text field changes for undo functionality"""
        # Track focus in to record original value
        entry_widget.bind("<FocusIn>", lambda e, widget=entry_widget, id=field_id: 
                        self.on_text_field_focus_in(widget, id))
        
        # Track focus out to record changes
        entry_widget.bind("<FocusOut>", lambda e, widget=entry_widget, id=field_id: 
                        self.on_text_field_focus_out(widget, id))

    def on_text_field_focus_in(self, widget, field_id):
        """Record original value when focusing on a text field"""
        # Store original value with a unique ID
        self.text_field_original_values[field_id] = widget.get()

    def on_text_field_focus_out(self, widget, field_id):
        """Record changes when leaving a text field"""
        new_value = widget.get()
        original_value = self.text_field_original_values.get(field_id, "")
        
        # Only record if there was a change
        if new_value != original_value:
            self.undo_stack.append({
                'type': 'text_change',
                'field_id': field_id,
                'widget': widget,
                'old_value': original_value,
                'new_value': new_value
            })
            
            # Limit undo stack size
            if len(self.undo_stack) > self.max_undo_stack:
                self.undo_stack.pop(0)
    
    def undo_last_action(self, event=None):
        """Handle Ctrl+Z to undo the last action"""
        if not self.undo_stack:
            return
            
        action = self.undo_stack.pop()
        action_type = action.get('type')
        
        if action_type == 'text_change':
            # Get the widget and original value
            widget = action.get('widget')
            old_value = action.get('old_value', "")
            
            # Check if widget still exists
            try:
                widget.winfo_exists()
                # Restore the original value
                widget.delete(0, tk.END)
                widget.insert(0, old_value)
            except:
                return
        
        elif action_type == 'remove_command':
            group_name = action.get('group_name')
            command_data = action.get('command_data')
            command_index = action.get('command_index')
            
            # Restore the command
            if group_name in self.workflow and group_name in self.groups_frames:
                if command_index <= len(self.workflow[group_name]):
                    self.workflow[group_name].insert(command_index, command_data)
                    self.add_command(group_name, command_data)
        
        elif action_type == 'remove_group':
            group_name = action.get('group_name')
            group_data = action.get('group_data')
            
            # Restore the group
            self.workflow[group_name] = group_data
            self.add_group(group_name, is_loading=True)
            for command_data in group_data:
                self.add_command(group_name, command_data)
    
    def clear_focus(self, event=None):
        """Clear focus from any input field when clicking on the window or pressing Enter"""
        # If triggered by Enter key
        if event and event.type == tk.EventType.KeyPress:
            # Clear focus by setting focus to the root window
            self.root.focus_set()
            return
            
        # For mouse clicks, check if the click is on an entry widget or its parent widget
        clicked_widget = event.widget
        
        # Don't clear focus if clicking on an entry or a dropdown
        if isinstance(clicked_widget, (tk.Entry, ttk.Combobox)) or clicked_widget.winfo_class() in ('TEntry', 'TCombobox'):
            return
        
        # Don't clear focus if clicking on a parent of an entry that's currently focused
        current_focus = self.root.focus_get()
        if current_focus and isinstance(current_focus, (tk.Entry, ttk.Combobox)):
            parent = clicked_widget
            while parent:
                if parent == current_focus:
                    return
                try:
                    parent = parent.master
                except:
                    break
        
        # Clear focus by setting focus to the root window
        self.root.focus_set()
    
    def flash_widget(self, widget, flash_count=1):
        """Briefly highlight a widget to provide visual feedback for move operations"""
        original_bg = widget.cget("background")
        
        def flash_cycle(count):
            if count <= 0:
                widget.configure(background=original_bg)
                return
            
            # Change to highlight color
            widget.configure(background="#A0C8F0")  # Light blue
            
            # Schedule change back after a short delay
            widget.after(100, lambda: widget.configure(background=original_bg))
            
            # Schedule next flash
            widget.after(200, lambda: flash_cycle(count-1))
        
        flash_cycle(flash_count)
    
    def move_group(self, group_name, direction):
        """Move a group up or down in the workflow execution order"""
        # Get all group names in order
        group_names = list(self.workflow.keys())
        
        # Find current index of the group
        try:
            current_index = group_names.index(group_name)
        except ValueError:
            return
        
        # Calculate new index based on direction
        if direction == "up" and current_index > 0:
            new_index = current_index - 1
        elif direction == "down" and current_index < len(group_names) - 1:
            new_index = current_index + 1
        else:
            return  # Can't move further in that direction
        
        # Get the target group name
        target_group_name = group_names[new_index]
        
        # Create a new ordered workflow to maintain the correct sequence
        new_workflow = {}
        for i, name in enumerate(group_names):
            if i == new_index:
                if direction == "up":
                    new_workflow[group_name] = self.workflow[group_name]
                    new_workflow[target_group_name] = self.workflow[target_group_name]
                else:  
                    new_workflow[target_group_name] = self.workflow[target_group_name]
                    new_workflow[group_name] = self.workflow[group_name]
            elif i == current_index:
                continue
            else:
                new_workflow[name] = self.workflow[name]
        
        # Update the workflow dictionary with the new order
        self.workflow = new_workflow
        
        # Collect all the frames in their current grid positions
        frames_with_positions = []
        for name, frame in self.groups_frames.items():
            frames_with_positions.append((name, frame, frame.grid_info()['row']))
        
        # Sort frames by their current row position
        frames_with_positions.sort(key=lambda x: x[2])
        
        # Rearrange the groups_frames dictionary to match the new workflow order
        self.groups_frames = {name: self.groups_frames[name] for name in new_workflow.keys()}
        
        # Re-grid all frames in the correct order
        for i, (name, frame, _) in enumerate(frames_with_positions):
            if name == group_name:
                # Move this frame to the new index position
                frame.grid(row=new_index, column=0, sticky="ew", padx=5, pady=5)
            elif name == target_group_name:
                # Move the target frame to the current index position
                frame.grid(row=current_index, column=0, sticky="ew", padx=5, pady=5)
            else:
                # Keep other frames in their original positions
                frame.grid(row=i, column=0, sticky="ew", padx=5, pady=5)
        
        # Visual feedback for the moved frame
        self.flash_widget(self.groups_frames[group_name])

    def move_command(self, group_name, command_frame, direction):
        """
        Final solution for moving commands up/down within a group
        Uses direct array manipulation and complete UI refresh
        """
        if group_name not in self.workflow or group_name not in self.groups_frames:
            return
        
        # Get the commands frame for this group
        commands_frame = self.groups_frames[group_name].commands_frame
        
        # Get all command frames in current order
        command_frames = commands_frame.winfo_children()
        frame_count = len(command_frames)
        
        # Find the current index of the command to move
        try:
            current_index = command_frames.index(command_frame)
        except ValueError:
            return
        
        # Calculate new index based on direction
        if direction == "up" and current_index > 0:
            new_index = current_index - 1
        elif direction == "down" and current_index < len(command_frames) - 1:
            new_index = current_index + 1
        else:
            return
        
        # Update all workflow data before making changes
        for i, cmd_frame in enumerate(command_frames):
            self.update_workflow_command(group_name, cmd_frame)
        
        # Print current workflow data
        for i, cmd in enumerate(self.workflow[group_name]):
            cmd_info = f"{cmd.get('command')}"
            args = cmd.get('args', {})
            if 'keys' in args:
                cmd_info += f" - keys: {args.get('keys')}"
        
        # Create a reordered copy of the workflow data
        reordered_workflow = self.workflow[group_name].copy()

        # Move the command in the reordered workflow
        command_data = reordered_workflow.pop(current_index)
        reordered_workflow.insert(new_index, command_data)
        
        # Update the workflow with the reordered data
        self.workflow[group_name] = reordered_workflow
        
        # Print reordered workflow data
        for i, cmd in enumerate(self.workflow[group_name]):
            cmd_info = f"{cmd.get('command')}"
            args = cmd.get('args', {})
            if 'keys' in args:
                cmd_info += f" - keys: {args.get('keys')}"

        for frame in command_frames:
            frame.destroy()
        
        # Rebuild all commands from scratch with the updated data
        built_frames = []
        moved_frame = None
        
        for i, cmd_data in enumerate(reordered_workflow):
            new_frame = self.add_command(group_name, cmd_data)
            built_frames.append(new_frame)
            
            # If this is the moved command, track the new frame
            if i == new_index:
                moved_frame = new_frame
                        
        # Apply visual feedback to the moved command
        if moved_frame:
            self.flash_widget(moved_frame)

    def copy_group(self, group_name):
        """Copy a group and append it to the bottom of the workflow"""
        if group_name not in self.workflow:
            return
        
        # Update all commands in the group to ensure data is current
        commands_frame = self.groups_frames[group_name].commands_frame
        for command_frame in commands_frame.winfo_children():
            self.update_workflow_command(group_name, command_frame)
        
        # Create a copy of the group with a new name
        new_group_name = f"{group_name} (Copy)"
        
        # Add the new group with the copied data
        self.add_group(name=new_group_name, group_data=self.workflow[group_name])
        
        # Add visual feedback
        self.flash_widget(self.groups_frames[new_group_name])
        
        return new_group_name

    def copy_command(self, group_name, command_frame):
        """Copy a command and append it to the end of its group"""
        if group_name not in self.workflow or group_name not in self.groups_frames:
            return
        
        # Get the commands frame for this group
        commands_frame = self.groups_frames[group_name].commands_frame
        
        # Find the index of the command to copy
        command_index = self.get_command_index(group_name, command_frame)
        if command_index < 0:
            return
        
        # Ensure the command data is up to date
        self.update_workflow_command(group_name, command_frame)
        
        # Get the command data to copy
        if command_index >= len(self.workflow[group_name]):
            # Command might not be in the workflow yet
            return
        
        import copy
        command_data = copy.deepcopy(self.workflow[group_name][command_index])
        
        # Add the command copy to the end of the group
        new_command_frame = self.add_command(group_name, command_data)
        
        # Add visual feedback
        self.flash_widget(new_command_frame)
        
        return new_command_frame

    def add_command(self, group_name, command_data=None):
        if group_name not in self.workflow or group_name not in self.groups_frames:
            return
        
        # Get the commands frame for this group
        commands_frame = self.groups_frames[group_name].commands_frame
        next_row = 0
        for child in commands_frame.winfo_children():
            grid_info = child.grid_info()
            if 'row' in grid_info and grid_info['row'] >= next_row:
                next_row = grid_info['row'] + 1
        # Create command frame with dark theme colors
        command_frame = tk.Frame(commands_frame, bd=1, relief=tk.SOLID, 
                            bg=self.colors["frame_bg"])
        command_frame.grid(row=next_row, column=0, sticky="ew", padx=5, pady=2)
        command_frame.grid_columnconfigure(1, weight=1)
        
        dropdown_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['command_name_width']
        
        # Command type dropdown
        command_types = [
            "", "Send Hotkey", "Keyboard Type", "Keyboard Press", 
            "OpenURL", "Click Element", "Check by Image", 
            "Check by Image And Move", "Mouse Click", "Mouse Move", 
            "Connect Driver", "Pause"
        ]
        
        command_var = tk.StringVar()
        
        # Create OptionMenu with custom styles
        dropdown = tk.OptionMenu(command_frame, command_var, *command_types)
        dropdown.config(width=dropdown_width,
                    bg=self.colors["input_bg"],
                    fg=self.colors["fg"],
                    activebackground=self.colors["highlight"],
                    activeforeground=self.colors["fg"],
                    relief=tk.FLAT,
                    bd=0,
                    highlightthickness=1,
                    font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                    highlightbackground=self.colors["border"])
        
        # Style the dropdown menu itself
        dropdown["menu"].config(bg=self.colors["input_bg"],
                            fg=self.colors["fg"],
                            activebackground=self.colors["highlight"],
                            activeforeground=self.colors["fg"],
                            font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_tiny'], 'bold'),
                            bd=0)
        
        dropdown.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Args frame - will be populated when command type changes
        args_frame = tk.Frame(command_frame, bg=self.colors["frame_bg"])
        args_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Command buttons frame with dark theme
        buttons_frame = tk.Frame(command_frame, bg=self.colors["frame_bg"])
        buttons_frame.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        
        # Calculate button sizes based on window width
        btn_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['button_large_command']
        small_btn_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['button_small_command']
        
        common_props = {
            "bg": self.colors["button_bg"],
            "fg": self.colors["button_fg"],
            "activebackground": self.colors["highlight"],
            "activeforeground": self.colors["fg"],
            "font": ('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
            "relief": tk.FLAT,
            "bd": 0
        }

        # Define button configurations
        buttons_config = [
            {"text": "Test", "width": btn_width, "column": 0, 
            "command": lambda: self.test_workflow(
                group_name=group_name, 
                command_index=self.get_command_index(group_name, command_frame))},
            {"text": "Copy", "width": btn_width, "column": 1,
            "command": lambda: self.copy_command(group_name, command_frame)},
            {"text": "Remove", "width": btn_width, "column": 2,
            "command": lambda: self.remove_command(group_name, command_frame)},
            {"text": "↑", "width": small_btn_width, "column": 3,
            "command": lambda: self.move_command(group_name, command_frame, "up")},
            {"text": "↓", "width": small_btn_width, "column": 4,
            "command": lambda: self.move_command(group_name, command_frame, "down")}
        ]

        # Create buttons
        for btn in buttons_config:
            button_props = common_props.copy()
            button_props.update(btn)
            command = button_props.pop("command")
            column = button_props.pop("column")
            
            tk.Button(buttons_frame, command=command, **button_props).grid(
                row=0, column=column, padx=2)
        
        # Store the args frame reference
        command_frame.args_frame = args_frame
        
        # Define proper command change handler
        def on_command_change(*args):
            self.update_command_args(group_name, command_frame, command_var.get())
        
        # Bind command selection event using trace_add for OptionMenu
        command_var.trace_add("write", on_command_change)
        
        # Store command variable for reference in update_workflow_command
        command_frame.command_var = command_var
        
        # If loading from saved data
        if command_data:
            command_var.set(command_data.get('command', ''))
            args = command_data.get('args', {})
            if not isinstance(args, dict):
                args = {}
            self.update_command_args(group_name, command_frame, command_var.get(), args)
        
        return command_frame
    
    def update_command_args(self, group_name, command_frame, command_type, saved_args=None):
        """Updates command arguments UI using ratio-based widths instead of fixed widths"""
        # Clear previous args widgets
        args_frame = command_frame.args_frame
        for widget in args_frame.winfo_children():
            widget.destroy()
        
        # Ensure saved_args is a dictionary
        if saved_args is None:
            saved_args = {}
        elif not isinstance(saved_args, dict):
            saved_args = {}
        
        tiny_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['update_command_args_tiny_width']
        small_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['update_command_args_small_width']
        medium_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['update_command_args_medium_width']
        large_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['update_command_args_large_width']
        max_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['button_largupdate_command_args_max_width']
        
        arg_widgets = []
        
        if command_type == "Send Hotkey":
            lbl = tk.Label(args_frame, text="Keys (comma-separated):", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=medium_width,
                        bg=self.colors["input_bg"], fg=self.colors["fg"], font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                        insertbackground=self.colors["fg"])
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("keys", entry))
            # Add undo tracking for this field
            field_id = f"cmd_{id(command_frame)}_{group_name}_keys"
            self.setup_text_field_tracking(entry, field_id)
                
        elif command_type == "Keyboard Type":
            lbl = tk.Label(args_frame, text="Text to type:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=max_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                        bg=self.colors["input_bg"], fg=self.colors["fg"],
                        insertbackground=self.colors["fg"])
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("text", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_text"
            self.setup_text_field_tracking(entry, field_id)
                
        elif command_type == "Keyboard Press":
            lbl = tk.Label(args_frame, text="Key to press:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=small_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                        bg=self.colors["input_bg"], fg=self.colors["fg"],
                        insertbackground=self.colors["fg"])
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("key", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_key"
            self.setup_text_field_tracking(entry, field_id)
                
        elif command_type == "OpenURL":
            lbl = tk.Label(args_frame, text="URL:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=max_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                        bg=self.colors["input_bg"], fg=self.colors["fg"],
                        insertbackground=self.colors["fg"])
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("url", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_url"
            self.setup_text_field_tracking(entry, field_id)
                
        elif command_type == "Click Element":
            lbl = tk.Label(args_frame, text="XPath:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=max_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                        bg=self.colors["input_bg"], fg=self.colors["fg"],
                        insertbackground=self.colors["fg"])
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("full_x_path", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_xpath"
            self.setup_text_field_tracking(entry, field_id)
                
        elif command_type in ["Check by Image", "Check by Image And Move"]:
            lbl = tk.Label(args_frame, text="Image Path:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=large_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                        bg=self.colors["input_bg"], fg=self.colors["fg"],
                        insertbackground=self.colors["fg"])
            entry.pack(side=tk.LEFT, padx=2)
            browse_btn = tk.Button(args_frame, text="Browse", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                                bg=self.colors["button_bg"], 
                                fg=self.colors["button_fg"],
                                activebackground=self.colors["highlight"],
                                activeforeground=self.colors["fg"],
                                relief=tk.FLAT, bd=0,
                                command=lambda e=entry: self.browse_image(e))
            browse_btn.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("img_path", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_img_path"
            self.setup_text_field_tracking(entry, field_id)
                
            # Add ROI field
            roi_lbl = tk.Label(args_frame, text="Check Region:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                            bg=self.colors["frame_bg"], fg=self.colors["fg"])
            roi_lbl.pack(side=tk.LEFT, padx=2)
            roi_entry = tk.Entry(args_frame, width=medium_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                            bg=self.colors["input_bg"], fg=self.colors["fg"],
                            insertbackground=self.colors["fg"])
            roi_entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("roi", roi_entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_roi"
            self.setup_text_field_tracking(roi_entry, field_id)
                
            # Add Threshold field
            threshold_lbl = tk.Label(args_frame, text="Threshold:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                                bg=self.colors["frame_bg"], fg=self.colors["fg"])
            threshold_lbl.pack(side=tk.LEFT, padx=2)
            threshold_entry = tk.Entry(args_frame, width=tiny_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                                    bg=self.colors["input_bg"], fg=self.colors["fg"],
                                    insertbackground=self.colors["fg"])
            threshold_entry.insert(0, "0.8")  # Default threshold value
            threshold_entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("threshold", threshold_entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_threshold"
            self.setup_text_field_tracking(threshold_entry, field_id)
                
        elif command_type == "Mouse Move":
            lbl_x = tk.Label(args_frame, text="X:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl_x.pack(side=tk.LEFT, padx=2)
            entry_x = tk.Entry(args_frame, width=tiny_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                            bg=self.colors["input_bg"], fg=self.colors["fg"],
                            insertbackground=self.colors["fg"])
            entry_x.pack(side=tk.LEFT, padx=2)
                
            lbl_y = tk.Label(args_frame, text="Y:", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl_y.pack(side=tk.LEFT, padx=2)
            entry_y = tk.Entry(args_frame, width=tiny_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                            bg=self.colors["input_bg"], fg=self.colors["fg"],
                            insertbackground=self.colors["fg"])
            entry_y.pack(side=tk.LEFT, padx=2)
                
            arg_widgets.append(("x", entry_x))
            arg_widgets.append(("y", entry_y))

            field_id_x = f"cmd_{id(command_frame)}_{group_name}_x"
            field_id_y = f"cmd_{id(command_frame)}_{group_name}_y"
            self.setup_text_field_tracking(entry_x, field_id_x)
            self.setup_text_field_tracking(entry_y, field_id_y)
            
        elif command_type == "Pause":
            lbl = tk.Label(args_frame, text="Duration (seconds):", font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        bg=self.colors["frame_bg"], fg=self.colors["fg"])
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=tiny_width, font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'normal'),
                        bg=self.colors["input_bg"], fg=self.colors["fg"],
                        insertbackground=self.colors["fg"])
            entry.insert(0, "1.0")
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("duration", entry))
            
            field_id = f"cmd_{id(command_frame)}_{group_name}_duration"
            self.setup_text_field_tracking(entry, field_id)
        
        # Store arg widgets reference for saving
        command_frame.arg_widgets = arg_widgets
        
        # Fill with saved values if provided
        if saved_args:
            for key, widget in arg_widgets:
                if key in saved_args:
                    widget.delete(0, tk.END)  # Clear any default values first
                    if isinstance(saved_args[key], list):
                        if key == 'roi':  # Handle ROI list differently
                            widget.insert(0, ", ".join(map(str, saved_args[key])))
                        else:
                            widget.insert(0, ",".join(map(str, saved_args[key])))
                    else:
                        widget.insert(0, str(saved_args[key]))
        
        # Record command type change for undo if this is an update to an existing command
        group_commands = self.groups_frames[group_name].commands_frame.winfo_children()
        index = group_commands.index(command_frame)
        if 0 <= index < len(self.workflow[group_name]):
            old_command = self.workflow[group_name][index].get('command', '')
            if old_command != command_type and old_command:  # Only record if changing from a non-empty type
                self.undo_stack.append({
                    'type': 'command_type_change',
                    'group_name': group_name,
                    'command_index': index,
                    'old_type': old_command,
                    'old_args': self.workflow[group_name][index].get('args', {}),
                    'new_type': command_type
                })
                # Limit undo stack size
                if len(self.undo_stack) > self.max_undo_stack:
                    self.undo_stack.pop(0)
        
        # Add command to workflow if it's not already there
        self.update_workflow_command(group_name, command_frame)
    
    def add_group(self, name=None, is_loading=False, group_data=None):
        """
        Add a new group to the workflow with collapsible/expandable functionality
        
        Args:
            name: Name of the group (generated if not provided)
            is_loading: Flag indicating if loading from saved data
            group_data: Data for the group commands (for copying)
        """
        if not name:
            name = f"Group {len(self.workflow) + 1}"
        
        # Handle duplicate group names
        if not is_loading and name in self.workflow:
            # For copies, add a suffix
            original_name = name
            suffix = 1
            while name in self.workflow:
                name = f"{original_name} (Copy {suffix})"
                suffix += 1
        
        # Initialize group in workflow
        self.workflow[name] = self.workflow.get(name, [])
        
        # If copying, use the provided group data
        if group_data:
            import copy
            self.workflow[name] = copy.deepcopy(group_data)
        
        next_row = 0
        for frame in self.groups_frames.values():
            grid_info = frame.grid_info()
            if 'row' in grid_info and grid_info['row'] >= next_row:
                next_row = grid_info['row'] + 1
        
        # Create group frame with dark theme colors
        group_frame = tk.LabelFrame(self.groups_container, text="", bd=2, relief=tk.GROOVE,
                                bg=self.colors["frame_bg"], fg=self.colors["fg"])
        group_frame.grid(row=next_row, column=0, sticky="ew", padx=5, pady=5)
        self.groups_frames[name] = group_frame
        
        group_frame.grid_columnconfigure(0, weight=1)
        
        # Group header frame with dark theme colors
        header_frame = tk.Frame(group_frame, bg=self.colors["frame_bg"])
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(0, weight=0)
        for i in range(1, 8):  # Added one more column for collapse/expand button
            header_frame.grid_columnconfigure(i, weight=1)
        
        name_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['group_name_width']
        
        # Group name entry with dark theme colors
        name_var = tk.StringVar(value=name)
        name_entry = tk.Entry(header_frame, textvariable=name_var, width=name_width,
                        bg=self.colors["input_bg"], fg=self.colors["fg"], font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                        insertbackground=self.colors["fg"])
        
        name_entry.grid(row=0, column=0, padx=5, sticky="w")
        name_entry.bind("<FocusOut>", lambda e, old_name=name: self.update_group_name(old_name, name_var.get()))
        
        # Add undo tracking for group name
        field_id = f"group_name_{id(group_frame)}_{name}"
        self.setup_text_field_tracking(name_entry, field_id)
        
        # Store expanded state
        group_frame.expanded = tk.BooleanVar(value=True)
        
        # Toggle button for collapsing/expanding with dark theme colors
        toggle_button = tk.Button(
            header_frame, 
            text="▼", 
            width=2,
            bg=self.colors["button_bg"],
            fg=self.colors["button_fg"],
            activebackground=self.colors["highlight"],
            activeforeground=self.colors["fg"],
            relief=tk.FLAT,
            bd=0,
            command=lambda: self.toggle_group_expansion(name)
        )
        toggle_button.grid(row=0, column=1, padx=5, sticky="w")
        
        # Store reference to toggle button for updating its text
        group_frame.toggle_button = toggle_button
        
        # Calculate button sizes based on window width
        btn_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['button_large_group']
        small_btn_width = self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['button_small_group']
        
        # Group buttons
        btn_commands = [
            ("Add Command", lambda: self.add_command(name), btn_width),
            ("Test Group", lambda: self.test_workflow(group_name=name), btn_width),
            ("Copy Group", lambda: self.copy_group(name), btn_width),
            ("Remove Group", lambda: self.remove_group(name), btn_width),
            ("↑", lambda: self.move_group(name, direction="up"), small_btn_width),
            ("↓", lambda: self.move_group(name, direction="down"), small_btn_width)
        ]

        for i, (text, command, width) in enumerate(btn_commands):
            tk.Button(header_frame, text=text, command=command, 
                    width=width,
                    bg=self.colors["button_bg"],
                    fg=self.colors["button_fg"],
                    activebackground=self.colors["highlight"],
                    activeforeground=self.colors["fg"],
                    relief=tk.FLAT,
                    font=('Arial', self.geometries[(self.root.winfo_screenwidth(), self.root.winfo_screenheight())]['font_small'], 'bold'),
                    bd=0).grid(
                row=0, column=i+2, padx=5, sticky="w"
            )
        
        # Commands container frame with dark theme colors
        commands_frame = tk.Frame(group_frame, bg=self.colors["frame_bg"])
        commands_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        commands_frame.grid_columnconfigure(0, weight=1)
        
        # Store the commands frame reference in the group frame
        group_frame.commands_frame = commands_frame
        
        # Record group creation for undo if not loading an existing group
        if not is_loading:
            self.undo_stack.append({
                'type': 'group_create',
                'group_name': name
            })
            # Limit undo stack size
            if len(self.undo_stack) > self.max_undo_stack:
                self.undo_stack.pop(0)
        
        return group_frame
    
    def toggle_group_expansion(self, group_name):
        """Toggle the expanded/collapsed state of a group"""
        if group_name not in self.groups_frames:
            return
        
        group_frame = self.groups_frames[group_name]
        
        # Toggle the expanded state
        group_frame.expanded.set(not group_frame.expanded.get())
        
        # Get the commands frame
        commands_frame = group_frame.commands_frame
        
        if group_frame.expanded.get():
            # Show the commands frame
            commands_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
            # Update button text
            group_frame.toggle_button.config(text="▼")
        else:
            # Hide the commands frame
            commands_frame.grid_forget()
            # Update button text
            group_frame.toggle_button.config(text="►")
        
        # Update the scroll region after toggle
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_chrome_group(self):
        """Add a predefined group with Chrome launch commands and customizable profile"""
        # Create a group name that doesn't exist yet
        group_name = "Open Chrome"
        suffix = 1
        while group_name in self.workflow:
            group_name = f"Open Chrome {suffix}"
            suffix += 1
        
        # Create the group
        group_frame = self.add_group(group_name)
        
        # Add the commands to open Chrome
        commands = [
            {
                "command": "Send Hotkey",
                "args": {
                    "keys": ["win", "r"]
                }
            },
            {
                "command": "Keyboard Type",
                "args": {
                    "text": "cmd"
                }
            },
            {
                "command": "Keyboard Press",
                "args": {
                    "key": "enter"
                }
            },
            {
                "command": "Keyboard Type",
                "args": {
                    "text": "\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" --remote-debugging-port=9222 --profile-directory=\"Profile 1\""
                }
            },
            {
                "command": "Keyboard Press",
                "args": {
                    "key": "enter"
                }
            },
            {
                "command": "Connect Driver"
            }
        ]
        
        # Add each command to the group
        for command_data in commands:
            self.add_command(group_name, command_data)
        
        # Give visual feedback that group was added
        self.flash_widget(group_frame)
        
if __name__ == "__main__":
    root = tk.Tk()
    app = WorkflowBuilder(root)
    root.mainloop()