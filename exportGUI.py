import tkinter as tk
from tkinter import ttk
import configparser
import pandas as pd
import logging
from logging_config import setup_logging
import threading
from tkinter import messagebox
import json
import os

# Read configuration from config.config
config = configparser.ConfigParser()
config.read('config.config')

# Constants
DEBUG = config.getboolean('DEBUGGING', 'DEBUG', fallback=False)
setup_logging(DEBUG)
SETTINGS_FILE = 'persistance.json'

# Dropdown values as constants
ENEMY_TYPES = ['All', 'Automatons', 'Illuminate', 'Terminids']
SUBFACTIONS = [
    'All', 'Terminid Horde', 'Predator Strain', 'Spore Burst Strain', 
    'Automaton Legion', 'Jet Brigade', 'Incineration Corps', 
    'Jet Brigade & Incineration Corps', 'Illuminate Cult', 'The Great Host'
]
SECTORS = [
    'All', 'Akira Sector', 'Alstrad Sector', 'Altus Sector', 'Andromeda Sector', 'Arturion Sector', 'Barnard Sector', 'Borgus Sector', 'Cancri Sector', 'Cantolus Sector', 'Celeste Sector', 'Draco Sector', 'Falstaff Sector', 'Farsight Sector', 'Ferris Sector', 'Gallux Sector',
    'Gellert Sector', 'Gothmar Sector', 'Guang Sector', 'Hanzo Sector', 'Hawking Sector', 'Hydra Sector', 'Idun Sector', 'Iptus Sector', 'Jin Xi Sector', 'Kelvin Sector', 'Korpus Sector', "L'estrade Sector", 'Lacaille Sector', 'Leo Sector', 'Marspira Sector', 'Meridian Sector',
    'Mirin Sector', 'Morgon Sector', 'Nanos Sector', 'Omega Sector', 'Orion Sector', 'Quintus Sector', 'Rictus Sector', 'Rigel Sector', 'Sagan Sector', 'Saleria Sector', 'Severin Sector', 'Sol System', 'Sten Sector', 'Talus Sector', 'Tanis Sector', 'Tarragon Sector', 'Theseus Sector',
    'Trigon Sector', 'Umlaut Sector', 'Ursa Sector', 'Valdis Sector', 'Xi Tauri Sector', 'Xzar Sector', 'Ymir Sector'
]
PLANETS = [
    'All','Alaraph', 'Alathfar XI', 'Andar', 'Asperoth Prime', 'Keid', 'Kneth Port', 'Klaka 5', 'Kraz', 'Pathfinder V', 'Klen Dahth II', "Widow's Harbor", 'New Haven', 'Pilen V', 'Charbal-VII', 'Charon Prime', 'Martale', 'Marfark', 'Matar Bay', 'Mortax Prime', 'Kirrik', 'Wilford Station', 'Arkturus',
    'Pioneer II', 'Electra Bay', 'Deneb Secundus', 'Fornskogur II', 'Veil', 'Marre IV', 'Midasburg', 'Darrowsport', 'Hydrofall Prime', 'Ursica XI', 'Achird III', 'Achernar Secundus', 'Darius II', 'Prosperity Falls', 'Cerberus IIIc', 'Effluvia', 'Seyshel Beach', 'Fort Sanctuary', 'Kelvinor', "Martyr's Bay",
    'Freedom Peak', 'Viridia Prime', 'Obari', 'Sulfura', 'Nublaria I', 'Krakatwo', 'Ivis', 'Slif', 'Moradesh', 'Meridia', 'Crimsica', 'Estanu', 'Fori Prime', 'Bore Rock', 'Esker', 'Socorro III', 'Erson Sands', 'Prasa', 'Pollux 31', 'Polaris Prime', 'Pherkad Secundus', 'Grand Errant', 'Hadar', 'Haldus', 'Zea Rugosia',
    'Herthon Secundus', 'Kharst', 'Bashyr', 'Rasp', 'Acubens Prime', 'Adhara', 'Afoyay Bay', 'Minchir', 'Mintoria', 'Blistica', 'Zzaniah Prime', 'Zosma', 'Okul VI', 'Solghast', 'Diluvia', 'Elysian Meadows', 'Alderidge Cove', 'Bellatrix', 'Botein', 'Khandark', 'Heze Bay', 'Alairt III', 'Alamak VII', 'New Stockholm', 'Ain-5',
    'Mordia 9', 'Euphoria III', 'Skitter', 'Kuma', 'Aesir Pass', 'Vernen Wells', 'Menkent', 'Wraith', 'Atrama', 'Myradesh', 'Maw', 'Providence', 'Primordia', 'Krakabos', 'Iridica', 'Valgaard', 'Ratch', 'Acamar IV', 'Pandion-XXIV', 'Gacrux', 'Phact Bay', 'Gar Haren', 'Gatria', 'Zegema Paradise', 'Fort Justice', 'New Kiruna',
    'Igla', 'Emeria', 'Crucible', 'Volterra', 'Caramoor', 'Alta V', 'Inari', 'Navi VII', 'Omicron', 'Nabatea Secundus', 'Gemstone Bluffs', 'Epsilon Phoencis VI', 'Enuliale', 'Disapora X', 'Lesath', 'Penta', 'Chort Bay', 'Choohe', 'Ras Algethi', 'Propus', 'Halies Port', 'Haka', 'Curia', 'Barabos', 'Fenmire', 'Tarsh', 'Mastia',
    'Emorath', 'Ilduna Prime', 'Baldrick Prime', 'Liberty Ridge', 'Hellmire', 'Nivel 43', 'Zagon Prime', 'Oshaune', 'Myrium', 'Eukoria', 'Regnus', 'Mog', 'Dolph', 'Julheim', 'Bekvam III', 'Duma Tyr', 'Setia', 'Senge 23', 'Seasse', 'Hydrobius', 'Karlia', 'Terrek', 'Azterra', 'Fort Union', 'Cirrus', 'Heeth', "Angel's Venture",
    'Veld', 'Termadon', 'Stor Tha Prime', 'Spherion', 'Stout', 'Leng Secundus', 'Valmox', 'Iro', 'Grafmere', 'Kerth Secundus', 'Parsh', 'Oasis', 'Genesis Prime', 'Rogue 5', 'RD-4', 'Hesoe Prime', 'Hort', 'Rirga Bay', 'Oslo Station', 'Gunvald', 'Borea', 'Calypso', 'Outpost 32', 'Reaf', 'Irulta', 'Maia', 'Malevelon Creek', 'Durgen',
    'Ubanea', 'Tibit', 'Super Earth', 'Mars', 'Trandor', 'Peacock', 'Partion', 'Overgoe Prime', 'Azur Secundus', 'Shallus', 'Shelt', 'Gaellivare', 'Imber', 'Claorell', 'Vog-Sojoth', 'Clasa', 'Yed Prior', 'Zefia', 'Demiurg', 'East Iridium Trading Bay', 'Brink-2', 'Osupsam', 'Canopus', 'Bunda Secundus', 'The Weir', 'Kuper', 'Caph', 'Castor',
    'Tien Kwan', 'Lastofe', 'Varylia 5', 'Choepessa IV', 'Ustotu', 'Troost', 'Vandalon IV', 'Erata Prime', 'Fenrir III', 'Turing', 'Skaash', 'Acrab XI', 'Acrux IX', 'Gemma', 'Merga IV', 'Merak', 'Cyberstan', 'Aurora Bay', 'Mekbuda', 'Videmitarix Prime', 'Skat Bay', 'Sirius', 'Siemnot', 'Shete', 'Mort', 'P\u00F6pli IX', 'Ingmar', 'Mantes',
    'Draupnir', 'Meissa', 'Wasat', 'X-45', 'Vega Bay', 'Wezen'
]

# Theme settings
light_theme = {
    ".": { 
        "configure": {
            "background": "#f0f0f0",  # Light grey background
            "foreground": "#000000",  # Black text
        }
    },
    "TLabel": {
        "configure": {
            "background": "#ffffff",
            "foreground": "#000000",  # Black text
        }
    },
    "TButton": {
        "configure": {
            "background": "#e0e0e0",  # Light grey button
            "foreground": "#000000",  # Black text
        }
    },
    "TEntry": {
        "configure": {
            "background": "#ffffff",
            "foreground": "#000000",  # Black text
            "fieldbackground": "#ffffff",
            "insertcolor": "#000000",
            "bordercolor": "#c0c0c0",
            "lightcolor": "#ffffff",
            "darkcolor": "#c0c0c0",
        }
    },
    "TCheckbutton": {
        "configure": {
            "background": "#ffffff",
            "foreground": "#000000",  # Black text
            "indicatorbackground": "#ffffff", 
            "indicatorforeground": "#000000",
        }
    },
    "TCombobox": {
        "configure": {
            "background": "#ffffff",
            "foreground": "#000000",  # Black text
            "fieldbackground": "#ffffff",
            "insertcolor": "#000000",
            "bordercolor": "#c0c0c0",
            "lightcolor": "#ffffff",
            "darkcolor": "#c0c0c0",
            "arrowcolor": "#000000"
        },
    },
    "TFrame": {
        "configure": {
            "background": "#ffffff",
        }
    },
    "TLabelframe": {
        "configure": {
            "background": "#ffffff",
            "foreground": "#000000",
        }
    },
    "TLabelframe.Label": {
        "configure": {
            "background": "#ffffff",
            "foreground": "#000000",
        }
    },
    "TNotebook": {
        "configure": {
            "background": "#f0f0f0",
        }
    },
    "TNotebook.Tab": {
        "configure": {
            "background": "#e0e0e0",
            "foreground": "#000000",
        }
    },
    "Treeview": {
        "configure": {
            "background": "#ffffff",
            "foreground": "#000000",
            "fieldbackground": "#ffffff",
        }
    },
    "Treeview.Heading": {
        "configure": {
            "background": "#e0e0e0",
            "foreground": "#000000",
        }
    }
}

dark_theme = {
    ".": { 
        "configure": {
            "background": "#1e1e1e",  # Dark grey background
            "foreground": "white",    # White text
        }
    },
    "TLabel": {
        "configure": {
            "background": "#252526",
            "foreground": "white",    # White text
        }
    },
    "TButton": {
        "configure": {
            "background": "#444444",  # Dark gray button
            "foreground": "white",    # Gray text by default
        },
        "map": {
            "foreground": [("hover", "white"), ("active", "white")],
            "background": [("hover", "black"), ("active", "black")]
        }
    },
    "TEntry": {
        "configure": {
            "background": "#252526",
            "foreground": "white",    # White text
            "fieldbackground": "#3c3c3c",
            "insertcolor": "#a3a3a3",
            "bordercolor": "black",
            "lightcolor": "#4d4d4d",
            "darkcolor": "black",
        }
    },
    "TCheckbutton": {
        "configure": {
            "background": "#252526",
            "foreground": "white",    # White text
            "indicatorbackground": "white", 
            "indicatorforeground": "black",
        }
    },
    "TCombobox": {
        "configure": {
            "background": "#444444",
            "foreground": "black",
            "fieldbackground": "#444444",
            "insertcolor": "white",
            "bordercolor": "black",
            "lightcolor": "#4d4d4d",
            "darkcolor": "black",
            "arrowcolor": "gray",
        },
    },
    "TFrame": {
        "configure": {
            "background": "#252526",
        }
    },
    "TLabelframe": {
        "configure": {
            "background": "#252526",
            "foreground": "white",
        }
    },
    "TLabelframe.Label": {
        "configure": {
            "background": "#252526",
            "foreground": "white",
        }
    },
    "TNotebook": {
        "configure": {
            "background": "#444444",
        }
    },
    "TNotebook.Tab": {
        "configure": {
            "background": "#444444",
            "foreground": "white",
        }
    },
    "Treeview": {
        "configure": {
            "background": "#2d2d2d",
            "foreground": "white",
            "fieldbackground": "#2d2d2d",
        }
    },
    "Treeview.Heading": {
        "configure": {
            "background": "#444444",
            "foreground": "white",
        }
    }
}

THEMES = {
    "light": light_theme,
    "dark": dark_theme
}

def apply_theme(root, theme_name):
    """Apply the selected theme to all widgets."""
    if theme_name not in THEMES:
        logging.error(f"Unknown theme: {theme_name}")
        return
        
    theme = THEMES[theme_name]
    style = ttk.Style()
    style.theme_use('clam')  # Use 'clam' as a base theme
    
    # Apply theme styles to all widget types
    for widget_type, settings in theme.items():
        if 'configure' in settings:
            try:
                style.configure(widget_type, **settings['configure'])
            except Exception as e:
                logging.error(f"Error applying theme to {widget_type}: {e}")
                
        if 'map' in settings:
            try:
                style.map(widget_type, **settings['map'])
            except Exception as e:
                logging.error(f"Error applying map for {widget_type}: {e}")
    
    # Special handling for Combobox dropdown
    if theme_name == 'dark':
        root.option_add("*TCombobox*Listbox*Background", '#2d2d2d')
        root.option_add("*TCombobox*Listbox*Foreground", 'white')
    else:
        root.option_add("*TCombobox*Listbox*Background", '#ffffff')
        root.option_add("*TCombobox*Listbox*Foreground", 'black')
    
    # Configure the root background
    if '.' in theme and 'configure' in theme['.']:
        root_bg = theme['.']['configure'].get('background')
        if root_bg:
            root.configure(background=root_bg)
            
    return theme_name

def get_current_theme():
    if os.path.exists('settings.json'):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                return settings.get('theme', 'light')
        except Exception:
            return 'light'
    return 'light'

def apply_theme_from_settings(root):
    theme_name = get_current_theme()
    apply_theme(root, theme_name)

def create_filter_dropdown(parent, label_text, var, values, on_select, padx=0):
    label = ttk.Label(parent, text=label_text)
    label.pack(side=tk.LEFT, padx=(padx, 0))
    dropdown = ttk.Combobox(parent, textvariable=var, values=values)
    dropdown.current(0)
    dropdown.pack(side=tk.LEFT)
    dropdown.bind("<<ComboboxSelected>>", on_select)
    return dropdown


def main():
    # Create the main window
    root = tk.Tk()
    root.title("Excel Data Viewer")
    root.geometry("1980x1000")
    root.minsize(1050, 500)
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "SuperEarth.png")
        root._icon_image = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, root._icon_image)
    except Exception as e:
        logging.warning(f"Unable to load window icon: {e}")
    # Set current_theme from settings at the start
    current_theme = get_current_theme()
    apply_theme(root, current_theme)
    
    # Configure root grid layout
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    
    # Create a frame for the table
    table_frame = ttk.Frame(root)
    table_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    
    # Configure table_frame grid
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)
    
    # Create the button frame FIRST - before it's referenced
    button_frame = ttk.Frame(root)
    button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
    
    # Create the table with ttk.Treeview
    try:
        # Determine which file to use
        if DEBUG:
            excel_file = "mission_log_test.xlsx"
        else:
            excel_file = "mission_log.xlsx"
        
        # Create a label to show loading status
        status_label = ttk.Label(table_frame, text="Loading data...", font=("Arial", 12))
        status_label.grid(row=0, column=0, sticky="nsew")
        
        # Create the table structure (but don't load data yet)
        table = ttk.Treeview(table_frame, show="headings", selectmode="extended")
        
        # Variables for virtual scrolling
        PAGE_SIZE = 50  # Number of rows to load at once
        current_offset = 0  # Current position in the dataset
        total_rows = 0  # Total number of rows in the dataset
        filtered_df = None  # Will hold the filtered dataframe
        scroll_timer = None  # Timer for debouncing scroll events
        last_scroll_position = 0  # Track last scroll position
        
        # Function to load data in background
        def load_data():
            try:
                # Read only the header first to set up columns
                df_header = pd.read_excel(excel_file, nrows=0)
                columns = list(df_header.columns)
                
                # Configure columns on the main thread
                root.after(0, lambda: setup_columns(columns))
                
                # Store the dataframe for later use instead of loading all rows
                global full_data_df
                full_data_df = pd.read_excel(excel_file)
                
                # Set filtered_df to the full dataset initially
                nonlocal filtered_df, total_rows
                filtered_df = full_data_df
                total_rows = len(filtered_df)
                
                # Only load the first set of visible rows initially
                display_rows(0, PAGE_SIZE)
                
                # Update row counter
                update_row_counter()
                
                # Hide loading indicator when done with initial load
                root.after(0, lambda: status_label.grid_forget())
                    
            except Exception as e:
                root.after(0, lambda e=e: show_error(f"Error loading Excel file: {e}"))

        def display_rows(start_idx, count):
            # Clear existing rows
            for item in table.get_children():
                table.delete(item)
            
            # Check if we have a filtered dataframe
            if filtered_df is None or filtered_df.empty:
                return
                 
            # Make sure start_idx is within bounds
            start_idx = max(0, min(start_idx, len(filtered_df) - 1 if len(filtered_df) > 0 else 0))
            nonlocal current_offset
            current_offset = start_idx
            
            # Load only the visible chunk
            end_idx = min(start_idx + count, len(filtered_df))
            visible_df = filtered_df.iloc[start_idx:end_idx]
            
            # Insert visible rows
            for _, row in visible_df.iterrows():
                values = [str(val) if pd.notna(val) else "" for val in row]
                table.insert("", tk.END, values=values)
                
            # Update the row counter
            update_row_counter()
        
        def setup_columns(columns):
            table["columns"] = columns
            for col in columns:
                table.heading(col, text=col)
                table.column(col, width=100, anchor=tk.CENTER)
        
        def show_error(message):
            status_label.grid_forget()
            messagebox.showerror("Error", message)
            logging.info(message)
            
        # Row counter label - now button_frame exists
        row_counter = ttk.Label(button_frame, text="Showing rows 0-0 of 0")
        row_counter.pack(side=tk.LEFT, padx=(10, 0))
        
        def update_row_counter():
            end_idx = min(current_offset + PAGE_SIZE, total_rows)
            row_counter.config(text=f"Showing rows {current_offset+1}-{end_idx} of {total_rows}")
        
        # Handle scrollbar movements to implement virtual scrolling with debouncing
        def on_scroll(*args):
            # Get the current position of the scrollbar
            try:
                # Extract the scrollbar position from args (yview returns values 0.0 to 1.0)
                position = float(args[0])
                
                # Store the position for later use
                nonlocal last_scroll_position
                last_scroll_position = position
                
                # Cancel previous timer if it exists
                nonlocal scroll_timer
                if scroll_timer:
                    root.after_cancel(scroll_timer)
                
                # Set a new timer to update the display after scrolling stops
                scroll_timer = root.after(100, lambda: update_after_scroll(position))
                
            except (ValueError, IndexError):
                pass
            return True  # Continue normal scrolling behavior
        
        # Function to update display after scrolling stops (called by timer)
        def update_after_scroll(position):
            # Calculate the corresponding row index based on position
            if total_rows > 0:
                row_index = int(position * total_rows)
                # Only redraw if we've scrolled enough to show a new page
                if abs(row_index - current_offset) >= PAGE_SIZE / 2:
                    display_rows(row_index, PAGE_SIZE)
            
            # Reset the timer
            nonlocal scroll_timer
            scroll_timer = None
        
        # Function to handle mousewheel scrolling
        def on_mousewheel(event):
            # This helps smooth the mousewheel scrolling experience
            # Get current position
            nonlocal current_offset
            delta = -1 if event.delta > 0 else 1  # Invert for natural scrolling
            
            # Adjust the scroll speed
            scroll_amount = 3 * delta
            new_offset = current_offset + scroll_amount
            
            # Ensure we stay within bounds
            if 0 <= new_offset < total_rows:
                # Update the scrollbar position
                new_position = new_offset / total_rows if total_rows > 0 else 0
                y_scrollbar.set(new_position, new_position + (PAGE_SIZE / total_rows if total_rows > 0 else 1))
                
                # Only redraw if we've moved enough
                if abs(new_offset - current_offset) >= PAGE_SIZE / 4:
                    display_rows(new_offset, PAGE_SIZE)
        
        # Function to filter data based on all selected filters
        def filter_data():
            # Apply filters to the full dataset
            nonlocal filtered_df, total_rows, current_offset
            df = full_data_df.copy()
            
            # Apply enemy type filter
            if filters['enemy_type'] != 'All':
                df = df[df['Enemy Type'] == filters['enemy_type']]
            
            # Apply subfaction filter
            if filters['Enemy Subfaction'] != 'All':
                df = df[df['Enemy Subfaction'] == filters['Enemy Subfaction']]
                
            # Apply sector filter
            if filters['sector'] != 'All':
                df = df[df['Sector'] == filters['sector']]
                
            # Apply planet filter
            if filters['planet'] != 'All':
                df = df[df['Planet'] == filters['planet']]
            
            # Update our filtered dataframe
            filtered_df = df
            total_rows = len(filtered_df)
            current_offset = 0
            
            # Display the first page
            display_rows(0, PAGE_SIZE)
        
        # Start the loading thread
        threading.Thread(target=load_data, daemon=True).start()
            
    except Exception as e:
        logging.error(f"Error setting up table: {e}")
    
    # Add scrollbars
    y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=table.yview)
    x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=table.xview)
    table.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
    
    # Configure the scrollbar to use our virtual scrolling with improved performance
    # Use a better method for binding scrolling events
    def custom_yview(*args):
        on_scroll(args[1])
        return table.yview(*args)
        
    y_scrollbar.configure(command=custom_yview)
    
    # Bind mousewheel for smoother scrolling
    table.bind("<MouseWheel>", on_mousewheel)
    
    # Add keyboard navigation for smoother experience
    def on_key(event):
        nonlocal current_offset
        key = event.keysym
        
        if key == "Down":
            new_offset = current_offset + 1
            if new_offset < total_rows:
                if new_offset % PAGE_SIZE == 0:
                    display_rows(new_offset, PAGE_SIZE)
                else:
                    # Just update scrollbar position without redrawing
                    new_position = new_offset / total_rows if total_rows > 0 else 0
                    y_scrollbar.set(new_position, new_position + (PAGE_SIZE / total_rows if total_rows > 0 else 1))
                    current_offset = new_offset
                    update_row_counter()
                    
        elif key == "Up":
            new_offset = max(0, current_offset - 1)
            if new_offset % PAGE_SIZE == PAGE_SIZE - 1 or current_offset == 0:
                display_rows(new_offset, PAGE_SIZE)
            else:
                # Just update scrollbar position without redrawing
                new_position = new_offset / total_rows if total_rows > 0 else 0
                y_scrollbar.set(new_position, new_position + (PAGE_SIZE / total_rows if total_rows > 0 else 1))
                current_offset = new_offset
                update_row_counter()
                
        elif key == "Next":  # Page Down
            new_offset = min(total_rows - 1, current_offset + PAGE_SIZE)
            display_rows(new_offset, PAGE_SIZE)
            
        elif key == "Prior":  # Page Up
            new_offset = max(0, current_offset - PAGE_SIZE)
            display_rows(new_offset, PAGE_SIZE)
            
        elif key == "Home":
            display_rows(0, PAGE_SIZE)
            
        elif key == "End":
            display_rows(max(0, total_rows - PAGE_SIZE), PAGE_SIZE)
    
    # Bind keyboard navigation
    table.bind("<Key>", on_key)
    
    # Add navigation buttons
    def next_page():
        nonlocal current_offset
        new_offset = current_offset + PAGE_SIZE
        if new_offset < total_rows:
            display_rows(new_offset, PAGE_SIZE)
            
    def prev_page():
        nonlocal current_offset
        new_offset = max(0, current_offset - PAGE_SIZE)
        display_rows(new_offset, PAGE_SIZE)
    
    # Add navigation buttons to button_frame
    nav_frame = ttk.Frame(button_frame)
    nav_frame.pack(side=tk.LEFT, padx=(20, 0))
    
    prev_button = ttk.Button(nav_frame, text="Previous Page", command=prev_page)
    prev_button.pack(side=tk.LEFT)
    
    next_button = ttk.Button(nav_frame, text="Next Page", command=next_page)
    next_button.pack(side=tk.LEFT, padx=(5, 0))
    
    # Add a slider for adjusting page size
    page_size_frame = ttk.Frame(button_frame)
    page_size_frame.pack(side=tk.LEFT, padx=(20, 0))
    
    ttk.Label(page_size_frame, text="Rows per page:").pack(side=tk.LEFT)
    
    def update_page_size(event=None):
        nonlocal PAGE_SIZE
        try:
            new_size = int(page_size_var.get())
            if 10 <= new_size <= 200:
                PAGE_SIZE = new_size
                display_rows(current_offset, PAGE_SIZE)
        except ValueError:
            pass
    
    page_size_var = tk.StringVar(value=str(PAGE_SIZE))
    page_size_combo = ttk.Combobox(page_size_frame, textvariable=page_size_var, width=5, 
                                  values=["25", "50", "75", "100", "150", "200"])
    page_size_combo.pack(side=tk.LEFT, padx=(5, 0))
    page_size_combo.bind("<<ComboboxSelected>>", update_page_size)
    page_size_combo.bind("<Return>", update_page_size)
    
    # Grid layout for the table and scrollbars
    table.grid(row=0, column=0, sticky="nsew")
    y_scrollbar.grid(row=0, column=1, sticky="ns")
    x_scrollbar.grid(row=1, column=0, sticky="ew")
    
    # Add a button
    def button_action():
        selected = table.selection()
        if selected:
            selected_items = [table.item(item, "values") for item in selected]
            logging.info(f"Selected {len(selected_items)} items:")
            for item in selected_items:
                logging.info(item)
        else:
            logging.info("No item selected")
    
    # Add a quit button
    quit_button = ttk.Button(button_frame, text="Quit", command=root.quit)
    quit_button.pack(side=tk.RIGHT)

    # Add a process selection button
    button = ttk.Button(button_frame, text="Process Selection", command=button_action)
    button.pack(side=tk.RIGHT)

    # Theme is now only settable from settings.py
    
    # Add filters section
    # Global variables to track filter selections
    filters = {
        'enemy_type': 'All',
        'Enemy Subfaction': 'All',
        'sector': 'All',
        'planet': 'All'
    }
    
    # Enemy Type filter
    enemy_var = tk.StringVar()
    def on_enemy_select(event):
        filters['enemy_type'] = enemy_var.get()
        filter_data()
    enemy_dropdown = create_filter_dropdown(
        button_frame, "Select enemy Type:", enemy_var, ENEMY_TYPES, on_enemy_select
    )

    # Subfaction filter
    subfaction_var = tk.StringVar()
    def on_subfaction_select(event):
        filters['Enemy Subfaction'] = subfaction_var.get()
        filter_data()
    subfaction_dropdown = create_filter_dropdown(
        button_frame, "Select subfaction:", subfaction_var, SUBFACTIONS, on_subfaction_select, padx=10
    )

    # Sector filter
    sector_var = tk.StringVar()
    def on_sector_select(event):
        filters['sector'] = sector_var.get()
        filter_data()
    sector_dropdown = create_filter_dropdown(
        button_frame, "Select sector:", sector_var, SECTORS, on_sector_select, padx=10
    )

    # Planet filter
    planet_var = tk.StringVar()
    def on_planet_select(event):
        filters['planet'] = planet_var.get()
        filter_data()
    planet_dropdown = create_filter_dropdown(
        button_frame, "Select planet:", planet_var, PLANETS, on_planet_select, padx=10
    )

    # Add a button to clear filters
    def clear_filters():
        filters['enemy_type'] = 'All'
        filters['Enemy Subfaction'] = 'All'
        filters['sector'] = 'All'
        filters['planet'] = 'All'
        
        enemy_dropdown.current(0)
        subfaction_dropdown.current(0)
        sector_dropdown.current(0)
        planet_dropdown.current(0)
        
        filter_data()
    clear_button = ttk.Button(button_frame, text="Clear Filters", command=clear_filters)
    clear_button.pack(side=tk.LEFT, padx=(10, 0))
    
    # Run the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()