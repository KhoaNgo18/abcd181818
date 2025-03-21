import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import tempfile
import os
import sys
import importlib.util
import time
 # Try to import required libraries
import pyautogui
import threading
import time
import keyboard  # For detecting key presses
import cv2
import numpy as np

SIZE = "1400x600"

class WorkflowBuilder:
    def __init__(self, root):
        
        self.undo_stack = []
        self.max_undo_stack = 20
        self.text_field_original_values = {}
        
        self.root = root
        self.root.title("Workflow Builder")
        self.root.geometry(SIZE)
        self.root.bind("<Control-z>", self.undo_last_action)
        self.root.bind("<Button-1>", self.clear_focus)
        self.root.bind("<Return>", self.clear_focus)
        
        self.workflow = {}
        self.groups_frames = {}
        self.backend_module = None
        
        # Try to import the backend module
        self.load_backend_module()
        
        # Main frame with scrollbar
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Button frame
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        tk.Button(self.button_frame, text="Add Group", command=self.add_group).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Save Workflow", command=self.save_workflow).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Load Workflow", command=self.load_workflow).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Test Workflow", command=self.test_workflow).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Get Mouse Position", command=self.get_mouse_position).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Select ROI", command=self.select_roi_from_image).pack(side=tk.LEFT, padx=5)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame inside canvas for groups
        self.groups_container = tk.Frame(self.canvas)
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.groups_container, anchor="nw")
        
        # Configure canvas scrolling
        self.groups_container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
    
    def on_frame_configure(self, event):
        # Update the scrollregion when the inner frame changes size
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        # Update the width of the window to match the canvas
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def on_mousewheel(self, event):
        # Scroll canvas with mouse wheel
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def add_group(self, name=None, is_loading=False):
        if not name:
            name = f"Group {len(self.workflow) + 1}"
        
        if not is_loading and name in self.workflow:
            messagebox.showerror("Error", "Group already exists!")
            return
        
        # Initialize group in workflow
        self.workflow[name] = self.workflow.get(name, [])
        
        # Create group frame
        group_frame = tk.LabelFrame(self.groups_container, text="", bd=2, relief=tk.GROOVE)
        group_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        self.groups_frames[name] = group_frame
        
        # Group header frame
        header_frame = tk.Frame(group_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Group name entry
        name_var = tk.StringVar(value=name)
        name_entry = tk.Entry(header_frame, textvariable=name_var, width=20)
        name_entry.pack(side=tk.LEFT, padx=5)
        name_entry.bind("<FocusOut>", lambda e, old_name=name: self.update_group_name(old_name, name_var.get()))
        
        # Add undo tracking for group name
        field_id = f"group_name_{id(group_frame)}_{name}"
        self.setup_text_field_tracking(name_entry, field_id)
        
        # Group buttons
        tk.Button(header_frame, text="Add Command", command=lambda: self.add_command(name)).pack(side=tk.LEFT, padx=5)
        tk.Button(header_frame, text="Test Group", command=lambda: self.test_workflow(group_name=name)).pack(side=tk.LEFT, padx=5)
        tk.Button(header_frame, text="Remove Group", command=lambda: self.remove_group(name)).pack(side=tk.LEFT, padx=5)
        
        # Commands container frame
        commands_frame = tk.Frame(group_frame)
        commands_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        
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

    def add_command(self, group_name, command_data=None):
        if group_name not in self.workflow or group_name not in self.groups_frames:
            return
        
        # Get the commands frame for this group
        commands_frame = self.groups_frames[group_name].commands_frame
        
        # Create command frame
        command_frame = tk.Frame(commands_frame, bd=1, relief=tk.SOLID)
        command_frame.pack(fill=tk.X, padx=5, pady=2, expand=True)
        
        # Command type dropdown
        command_types = [
            "", "Send Hotkey", "Keyboard Type", "Keyboard Press", 
            "OpenURL", "Click Element", "Check by Image", 
            "Check by Image And Move", "Mouse Click", "Mouse Move", "Connect Driver"
        ]
        
        command_var = tk.StringVar()
        command_dropdown = ttk.Combobox(command_frame, textvariable=command_var, values=command_types, width=20)
        command_dropdown.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Args frame - will be populated when command type changes
        args_frame = tk.Frame(command_frame)
        args_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Command buttons
        buttons_frame = tk.Frame(command_frame)
        buttons_frame.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Test command button
        tk.Button(buttons_frame, text="Test", command=lambda: self.test_workflow(
            group_name=group_name, 
            command_index=self.get_command_index(group_name, command_frame)
        )).pack(side=tk.LEFT, padx=2)
        
        # Remove button
        tk.Button(buttons_frame, text="Remove", command=lambda: self.remove_command(group_name, command_frame)).pack(side=tk.LEFT, padx=2)
        
        # Store the args frame reference
        command_frame.args_frame = args_frame
        
        # Bind command selection event
        command_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_command_args(group_name, command_frame, command_var.get()))
        
        # If loading from saved data
        if command_data:
            command_var.set(command_data.get('command', ''))
            args = command_data.get('args', {})
            if not isinstance(args, dict):
                args = {}
            self.update_command_args(group_name, command_frame, command_var.get(), args)
        
        return command_frame
    
    def update_command_args(self, group_name, command_frame, command_type, saved_args=None):
        # Clear previous args widgets
        args_frame = command_frame.args_frame
        for widget in args_frame.winfo_children():
            widget.destroy()
        
        # Ensure saved_args is a dictionary
        if saved_args is None:
            saved_args = {}
        elif not isinstance(saved_args, dict):
            saved_args = {}
                
        # Add appropriate input fields based on command type
        arg_widgets = []
        
        if command_type == "Send Hotkey":
            lbl = tk.Label(args_frame, text="Keys (comma-separated):")
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=20)
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("keys", entry))
            # Add undo tracking for this field
            field_id = f"cmd_{id(command_frame)}_{group_name}_keys"
            self.setup_text_field_tracking(entry, field_id)
            
        elif command_type == "Keyboard Type":
            lbl = tk.Label(args_frame, text="Text to type:")
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=100)
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("text", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_text"
            self.setup_text_field_tracking(entry, field_id)
            
        elif command_type == "Keyboard Press":
            lbl = tk.Label(args_frame, text="Key to press:")
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=10)
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("key", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_key"
            self.setup_text_field_tracking(entry, field_id)
            
        elif command_type == "OpenURL":
            lbl = tk.Label(args_frame, text="URL:")
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=100)
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("url", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_url"
            self.setup_text_field_tracking(entry, field_id)
            
        elif command_type == "Click Element":
            lbl = tk.Label(args_frame, text="XPath:")
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=100)
            entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("full_x_path", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_xpath"
            self.setup_text_field_tracking(entry, field_id)
            
        elif command_type in ["Check by Image", "Check by Image And Move"]:
            lbl = tk.Label(args_frame, text="Image Path:")
            lbl.pack(side=tk.LEFT, padx=2)
            entry = tk.Entry(args_frame, width=80)
            entry.pack(side=tk.LEFT, padx=2)
            browse_btn = tk.Button(args_frame, text="Browse", command=lambda e=entry: self.browse_image(e))
            browse_btn.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("img_path", entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_img_path"
            self.setup_text_field_tracking(entry, field_id)
            
            # Add ROI field
            roi_lbl = tk.Label(args_frame, text="Check Region:")
            roi_lbl.pack(side=tk.LEFT, padx=2)
            roi_entry = tk.Entry(args_frame, width=20)
            roi_entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("roi", roi_entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_roi"
            self.setup_text_field_tracking(roi_entry, field_id)
            
            # Add Threshold field
            threshold_lbl = tk.Label(args_frame, text="Threshold:")
            threshold_lbl.pack(side=tk.LEFT, padx=2)
            threshold_entry = tk.Entry(args_frame, width=5)
            threshold_entry.insert(0, "0.8")  # Default threshold value
            threshold_entry.pack(side=tk.LEFT, padx=2)
            arg_widgets.append(("threshold", threshold_entry))
            # Add undo tracking
            field_id = f"cmd_{id(command_frame)}_{group_name}_threshold"
            self.setup_text_field_tracking(threshold_entry, field_id)
            
        elif command_type == "Mouse Move":
            lbl_x = tk.Label(args_frame, text="X:")
            lbl_x.pack(side=tk.LEFT, padx=2)
            entry_x = tk.Entry(args_frame, width=5)
            entry_x.pack(side=tk.LEFT, padx=2)
            
            lbl_y = tk.Label(args_frame, text="Y:")
            lbl_y.pack(side=tk.LEFT, padx=2)
            entry_y = tk.Entry(args_frame, width=5)
            entry_y.pack(side=tk.LEFT, padx=2)
            
            arg_widgets.append(("x", entry_x))
            arg_widgets.append(("y", entry_y))
            # Add undo tracking
            field_id_x = f"cmd_{id(command_frame)}_{group_name}_x"
            field_id_y = f"cmd_{id(command_frame)}_{group_name}_y"
            self.setup_text_field_tracking(entry_x, field_id_x)
            self.setup_text_field_tracking(entry_y, field_id_y)
        
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
    
    def browse_image(self, entry_widget):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def update_workflow_command(self, group_name, command_frame):
        # Get command type
        for widget in command_frame.winfo_children():
            if isinstance(widget, ttk.Combobox):
                command_type = widget.get()
                break
        else:
            return  # Command type not found
        
        # Get args from widgets
        args = {}
        for key, widget in getattr(command_frame, 'arg_widgets', []):
            value = widget.get()
            if ',' in value and key == 'keys':  # Handle comma-separated values
                args[key] = [v.strip() for v in value.split(',')]
            elif key in ['x', 'y']:  # Convert coordinates to integers
                try:
                    args[key] = int(value) if value else 0
                except ValueError:
                    args[key] = 0
            else:
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
        Test the workflow, a specific group, or a specific command
        
        Args:
            group_name: If provided, only test this group
            command_index: If provided with group_name, only test this specific command
        """
        import tempfile
        
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
            
            # Redirect stdout and stderr to capture logs
            stdout_capture = LogCapture()
            stderr_capture = LogCapture()
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            try:
                # Call the main function directly
                self.backend_module(temp_filename)
                success = True
            except Exception as e:
                success = False
                error_msg = str(e)
            finally:
                # Restore stdout and stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Clean up the temporary file
            os.unlink(temp_filename)
            
            # Get captured logs
            stdout_logs = stdout_capture.get_logs()
            stderr_logs = stderr_capture.get_logs()
            
            # Show results in a new window
            self.show_test_results(
                success=success if 'success' in locals() else False,
                stdout=stdout_logs,
                stderr=stderr_logs if 'stderr_logs' in locals() else (error_msg if 'error_msg' in locals() else "Unknown error"),
                test_type=test_type
            )
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to test workflow: {e}")
     
    def show_test_results(self, success, stdout, stderr, test_type):
        """Show test results in a scrollable window"""
        result_window = tk.Toplevel(self.root)
        result_window.title(f"Test Results - {test_type}")
        result_window.geometry(SIZE)
        
        # Status label
        status_frame = tk.Frame(result_window)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_label = tk.Label(
            status_frame, 
            text=f"Test {'SUCCEEDED' if success else 'FAILED'}", 
            fg="green" if success else "red",
            font=("Arial", 12, "bold")
        )
        status_label.pack(side=tk.LEFT)
        
        # Notebook for stdout/stderr
        notebook = ttk.Notebook(result_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Stdout tab
        stdout_frame = tk.Frame(notebook)
        notebook.add(stdout_frame, text="Output")
        
        stdout_scrollbar = tk.Scrollbar(stdout_frame)
        stdout_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        stdout_text = tk.Text(stdout_frame, wrap=tk.WORD, yscrollcommand=stdout_scrollbar.set)
        stdout_text.pack(fill=tk.BOTH, expand=True)
        stdout_scrollbar.config(command=stdout_text.yview)
        
        stdout_text.insert(tk.END, stdout)
        stdout_text.config(state=tk.DISABLED)
        
        # Stderr tab (only if there are errors)
        if stderr:
            stderr_frame = tk.Frame(notebook)
            notebook.add(stderr_frame, text="Errors")
            
            stderr_scrollbar = tk.Scrollbar(stderr_frame)
            stderr_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            stderr_text = tk.Text(stderr_frame, wrap=tk.WORD, yscrollcommand=stderr_scrollbar.set)
            stderr_text.pack(fill=tk.BOTH, expand=True)
            stderr_scrollbar.config(command=stderr_text.yview)
            
            stderr_text.insert(tk.END, stderr)
            stderr_text.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(result_window, text="Close", command=result_window.destroy).pack(pady=10)
         
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
            # Create a new window to display mouse position
            position_window = tk.Toplevel(self.root)
            position_window.title("Mouse Position Tracker")
            position_window.geometry("400x300")  # Increased size from 300x150
            position_window.resizable(True, True)  # Allow resizing
            
            # Label to display coordinates
            coordinates_var = tk.StringVar(value="Move your mouse...")
            coordinates_label = tk.Label(
                position_window, 
                textvariable=coordinates_var,
                font=("Arial", 18),  # Increased font size
                height=2 
            )
            coordinates_label.pack(pady=25)  # Increased padding
            
            # Instructions label
            instructions = tk.Label(
                position_window,
                text="Press ANY KEY to capture the current position",
                font=("Arial", 12),  # Increased font size
                wraplength=380  # Set text wrapping
            )
            instructions.pack(pady=10)  # Increased padding
            
            # Status label
            status_var = tk.StringVar(value="Tracking mouse...")
            status_label = tk.Label(
                position_window,
                textvariable=status_var,
                font=("Arial", 12),  # Increased font size
                fg="blue",
                wraplength=380  # Set text wrapping
            )
            status_label.pack(pady=15)  # Increased padding
            
            # Variable to store the last position
            last_position = [0, 0]
            
            # Flag to control the tracking loop
            tracking = True
            
            # Function to track mouse position
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
            
            # Function to detect key press and stop tracking
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
                    status_label.config(fg="green")
                    
                    # Show the re-capture button
                    recapture_button.pack(pady=10)
            
            # Function to restart tracking
            def restart_tracking():
                nonlocal tracking
                if not tracking:
                    # Reset status
                    status_var.set("Tracking mouse...")
                    status_label.config(fg="blue")
                    
                    # Hide recapture button
                    recapture_button.pack_forget()
                    
                    # Start tracking again
                    tracking = True
                    tracking_thread = threading.Thread(target=track_position, daemon=True)
                    tracking_thread.start()
                    
                    # Make sure window has focus
                    position_window.focus_force()
            
            # Create recapture button (initially hidden)
            recapture_button = tk.Button(
                position_window,
                text="Capture Again",
                font=("Arial", 11),
                bg="#e0e0e0",
                padx=10,
                command=restart_tracking
            )
            # Button will be shown only after position is captured
            
            # Start tracking in a separate thread
            tracking_thread = threading.Thread(target=track_position, daemon=True)
            tracking_thread.start()
            
            # Bind key press event to the window
            position_window.bind("<KeyPress>", on_key_press)
            
            # Make sure window has focus to capture key events
            position_window.focus_force()
            
            # Also use the keyboard library to catch global keypresses
            def global_key_handler(e):
                if tracking:
                    # Call our key handler
                    on_key_press(None)
            
            # Add a keyboard hook
            keyboard.hook(global_key_handler)
            
            # Ensure thread is stopped and hook is removed when window closes
            def on_window_close():
                nonlocal tracking
                tracking = False
                keyboard.unhook_all()
                position_window.destroy()
            
            position_window.protocol("WM_DELETE_WINDOW", on_window_close)
            
        except ImportError as e:
            # Determine which package is missing
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
            result_window.geometry("400x200")
            
            # Show the ROI coordinates
            tk.Label(
                result_window, 
                text="Selected Region of Interest (ROI):", 
                font=("Arial", 12, "bold")
            ).pack(pady=10)
            
            roi_text = str(selected_roi)[1:-1]
            tk.Label(
                result_window,
                text=roi_text,
                font=("Arial", 14)
            ).pack(pady=5)
            
            # Image details
            image = cv2.imread(file_path)
            height, width = image.shape[:2]
            image_info = f"Image: {os.path.basename(file_path)}\nDimensions: {width} x {height}"
            tk.Label(
                result_window,
                text=image_info,
                font=("Arial", 10),
                justify=tk.LEFT
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
                font=("Arial", 11)
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
    
    def undo_last_action(self, event=None):
        """Handle Ctrl+Z to undo the last action"""
        if not self.undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo")
            return
            
        action = self.undo_stack.pop()
        action_type = action.get('type')
        
        if action_type == 'remove_command':
            group_name = action.get('group_name')
            command_data = action.get('command_data')
            command_index = action.get('command_index')
            
            # Restore the command
            if group_name in self.workflow and group_name in self.groups_frames:
                if command_index <= len(self.workflow[group_name]):
                    self.workflow[group_name].insert(command_index, command_data)
                    self.add_command(group_name, command_data)
                    messagebox.showinfo("Undo", f"Restored command in group '{group_name}'")
        
        elif action_type == 'remove_group':
            group_name = action.get('group_name')
            group_data = action.get('group_data')
            
            # Restore the group
            self.workflow[group_name] = group_data
            self.add_group(group_name, is_loading=True)
            for command_data in group_data:
                self.add_command(group_name, command_data)
            messagebox.showinfo("Undo", f"Restored group '{group_name}'")
    
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
    
if __name__ == "__main__":
    root = tk.Tk()
    app = WorkflowBuilder(root)
    root.mainloop()