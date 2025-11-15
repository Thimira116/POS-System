import tkinter as tk
from tkinter import ttk, messagebox, simpledialog 
import json
import os
import datetime 

# --- NEW --- Imports for charting
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Constants ---
PRODUCTS_DB = 'products.json'
INVENTORY_DB = 'inventory.json'
RECEIPT_FOLDER = 'receipts'
CONFIG_DB = 'config.json' 
SALES_LOG_DB = 'sales_log.json' # --- NEW --- File to store sales data
LOW_STOCK_THRESHOLD = 20 
CURRENCY_SYMBOL = 'Rs.' # Set global currency symbol

# --- Data Handling Functions ---

def load_data(filename):
    """Loads data from a JSON file. Returns {} or [] if the file doesn't exist."""
    if not os.path.exists(filename):
        # --- MODIFIED --- Return list for sales log, dict for others
        return [] if filename == SALES_LOG_DB else {}
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        if filename != CONFIG_DB:
            messagebox.showerror("Error", f"Could not read {filename}. File may be corrupt.")
        return [] if filename == SALES_LOG_DB else {}

def save_data(filename, data):
    """Saves data to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        messagebox.showerror("Error", f"Could not save to {filename}: {e}")

# --- NEW --- Function to log individual sale items
def log_sale(cart):
    """Loads the sales log, appends new sales from the cart, and saves it."""
    sales_log = load_data(SALES_LOG_DB)
    if not isinstance(sales_log, list):
        sales_log = [] # Ensure it's a list if file was empty or corrupt

    sale_time = datetime.datetime.now().isoformat()
    
    for barcode, item in cart.items():
        log_entry = {
            'timestamp': sale_time,
            'barcode': barcode,
            'name': item['name'],
            'quantity': item['quantity'],
            'line_total': item['line_total'],
            'is_weighted': item['is_weighted']
        }
        sales_log.append(log_entry)
        
    save_data(SALES_LOG_DB, sales_log)

def load_shop_name():
    """Loads the shop name from the config file, defaulting to a placeholder."""
    config = load_data(CONFIG_DB)
    return config.get('shop_name', 'Simple Grocery Shop') 

def save_shop_name(name):
    """Saves the shop name to the config file."""
    config = load_data(CONFIG_DB)
    config['shop_name'] = name
    save_data(CONFIG_DB, config)


### PROGRAMMATIC SHOP NAME CHANGE ###
# Use this block to change the shop name directly in the source code.
# 1. Uncomment the two lines below.
# 2. Set the desired name.
# 3. Run the app ONCE to update the config file.
# 4. Re-comment the lines out to prevent overwriting on future launches.

# new_shop_name = "Grocery Mart" 
# save_shop_name(new_shop_name)

#####################################


def check_for_low_stock():
    """Checks if any product's quantity is below the LOW_STOCK_THRESHOLD."""
    products = load_data(PRODUCTS_DB)
    inventory = load_data(INVENTORY_DB)
    
    for barcode in products.keys():
        quantity = inventory.get(barcode, {}).get('quantity', 0)
        # Check if quantity is below the threshold
        if quantity < LOW_STOCK_THRESHOLD:
            return True # Found at least one low stock item
    return False

# --- Main Application Class ---

class GroceryPOSApp(tk.Tk):
    """Main application container."""
    def __init__(self):
        super().__init__()
        self.title("Grocery POS System")
        self.geometry("1000x700")

        # The StringVar ensures name changes update automatically across all frames
        self.shop_name_var = tk.StringVar(self, value=load_shop_name()) 

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        # --- MODIFIED --- Added BillHistoryFrame and AnalyticsFrame to the loop
        for F in (POSFrame, InventoryFrame, BillHistoryFrame, AnalyticsFrame):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(POSFrame)
        
    def show_frame(self, cont):
        """Brings the requested frame to the front and refreshes data."""
        frame = self.frames[cont]
        frame.tkraise()
        if hasattr(frame, "refresh_data"):
            frame.refresh_data()

# --- POS (Billing) Frame ---

class POSFrame(tk.Frame):
    """The main billing and checkout screen."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.products = {}
        self.inventory = {}
        self.cart = {} 
        self.subtotal = 0.0 
        self.final_total = 0.0 
        
        self.configure(bg="#f0f0f0")
        self.create_widgets()
        self.refresh_data() # Initial data load and dot check

    def refresh_data(self):
        """Load fresh data from the JSON 'databases' and update the low stock dot."""
        self.products = load_data(PRODUCTS_DB)
        self.inventory = load_data(INVENTORY_DB)
        self.update_low_stock_dot()

    def update_low_stock_dot(self):
        """Checks for low stock and updates the red dot visibility on the button."""
        if check_for_low_stock():
            # Show the red dot
            self.dot_canvas.itemconfig(self.dot, state='normal')
        else:
            # Hide the red dot
            self.dot_canvas.itemconfig(self.dot, state='hidden')
        
    def create_widgets(self):
        # --- Navigation ---
        nav_frame = tk.Frame(self, bg="#34495e")
        nav_frame.pack(side="top", fill="x")
        
        # Shop Name is a static label
        shop_name_frame = tk.Frame(nav_frame, bg="#34495e")
        shop_name_frame.pack(side="left", padx=10, pady=5)
        
        tk.Label(shop_name_frame, textvariable=self.controller.shop_name_var, 
                 font=("Arial", 12, "bold"), fg="#e0e0e0", bg="#34495e").pack(side="left", padx=5)
        
        # Original Title
        tk.Label(nav_frame, text="Billing Screen", font=("Arial", 16, "bold"), fg="white", bg="#34495e").pack(side="left", padx=10, pady=10)
        
        # --- Inventory Button with Red Dot Notification ---
        inv_button_container = tk.Frame(nav_frame, bg="#34495e")
        inv_button_container.pack(side="right", padx=10, pady=10)
        
        # --- Analytics Button
        tk.Button(inv_button_container, text="Sales Analytics", font=("Arial", 10), 
                  command=lambda: self.controller.show_frame(AnalyticsFrame)).pack(side="left", padx=5)
        
         # Bill History Button
        tk.Button(inv_button_container, text="Bill History", font=("Arial", 10), 
                  command=lambda: self.controller.show_frame(BillHistoryFrame)).pack(side="left", padx=5)
        
        # Inventory Button
        tk.Button(inv_button_container, text="Inventory", font=("Arial", 10), 
                  command=lambda: self.controller.show_frame(InventoryFrame)).pack(side="left")

        # Canvas for the notification dot
        self.dot_canvas = tk.Canvas(inv_button_container, width=12, height=12, bg="#34495e", highlightthickness=0)
        self.dot_canvas.pack(side="right", padx=5)

        # Draw the red dot (circle)
        self.dot = self.dot_canvas.create_oval(2, 2, 10, 10, fill="red", outline="red")
        self.dot_canvas.itemconfig(self.dot, state='hidden') # Hidden by default

        # --- Main Content Area (rest of the POS widgets unchanged) ---
        main_frame = tk.Frame(self, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # --- Left Side (Scanning & Cart) ---
        cart_frame = tk.Frame(main_frame, bg="white", bd=2, relief="groove")
        cart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        cart_frame.grid_columnconfigure(0, weight=1)
        cart_frame.grid_rowconfigure(2, weight=1)

        # Scanning Area (Unit Items with Quantity Input)
        scan_area = tk.Frame(cart_frame, bg="white")
        scan_area.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # tk.Label(scan_area, text="Product Name:", font=("Arial", 12), bg="white").pack(side="left", padx=(10,0))
        # self.product_name_entry = ttk.Entry(scan_area, font=("Arial", 12), width=15)
        # self.product_name_entry.pack(side="left", padx=5)
        
        tk.Label(scan_area, text="Scan Barcode:", font=("Arial", 12), bg="white").pack(side="left")
        self.barcode_entry = ttk.Entry(scan_area, font=("Arial", 12), width=15)
        self.barcode_entry.pack(side="left", padx=5)

        tk.Label(scan_area, text="Quantity:", font=("Arial", 12), bg="white").pack(side="left", padx=(10, 0))
        self.unit_quantity_entry = ttk.Entry(scan_area, font=("Arial", 12), width=5)
        self.unit_quantity_entry.insert(0, "1") 
        self.unit_quantity_entry.pack(side="left", padx=5)
        
        scan_button = ttk.Button(scan_area, text="Add Unit", command=self.scan_item)
        scan_button.pack(side="left", padx=5)

        # Weighted Item Area
        weight_area = tk.Frame(cart_frame, bg="white")
        weight_area.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        tk.Label(weight_area, text="Weighted Barcode:", font=("Arial", 12), bg="white").pack(side="left")
        self.weight_barcode_entry = ttk.Entry(weight_area, font=("Arial", 12), width=15)
        self.weight_barcode_entry.pack(side="left", padx=(5,0))
        self.weight_barcode_entry.insert(0, "W-")
        
        tk.Label(weight_area, text="Weight (kg):", font=("Arial", 12), bg="white").pack(side="left", padx=(10,0))
        self.weight_entry = ttk.Entry(weight_area, font=("Arial", 12), width=5)
        self.weight_entry.pack(side="left", padx=(5,0))
        
        ttk.Button(weight_area, text="Add Weight", command=self.add_weighted_item).pack(side="left", padx=5)

        # Cart Display
        cart_display_frame = tk.Frame(cart_frame, bg="white")
        cart_display_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
        # Currency change reflected here
        tk.Label(cart_display_frame, text=f"{'QTY':<8} {'ITEM':<30} {'PRICE':>10}", font=("Courier", 11, "bold"), anchor="w").pack(fill="x", padx=10)
        
        self.cart_list = tk.Listbox(cart_display_frame, font=("Courier", 11), height=15)
        sb = tk.Scrollbar(cart_display_frame, orient="vertical", command=self.cart_list.yview)
        self.cart_list.configure(yscrollcommand=sb.set)
        
        sb.pack(side="right", fill="y")
        self.cart_list.pack(side="left", fill="both", expand=True)

        # Cart Actions
        cart_action_frame = tk.Frame(cart_frame, bg="white")
        cart_action_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        ttk.Button(cart_action_frame, text="Remove Selected Item", command=self.remove_selected_item).pack(side="left", fill="x", expand=True)
        
        # --- Right Side (Total, Discount & Actions) ---
        actions_frame = tk.Frame(main_frame, bg="white", bd=2, relief="groove")
        actions_frame.grid(row=0, column=1, sticky="nsew")
        actions_frame.pack_propagate(False) 

        # Total Display
        total_frame = tk.Frame(actions_frame, bg="#ecf0f1", bd=1, relief="flat")
        total_frame.pack(fill="x", padx=20, pady=20)

        # Currency change reflected here
        self.subtotal_label = tk.Label(total_frame, text=f"Subtotal:{CURRENCY_SYMBOL}0.00", font=("Arial", 14), bg="#ecf0f1", anchor="e")
       
        self.subtotal_label.pack(fill="x", padx=10, pady=2)
        
        # Discount Input Area
        discount_input_frame = tk.Frame(total_frame, bg="#ecf0f1")
        discount_input_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(discount_input_frame, text="Discount (%):", font=("Arial", 14), bg="#ecf0f1").pack(side="left")
        
        self.discount_entry = ttk.Entry(discount_input_frame, font=("Arial", 14), width=5)
        self.discount_entry.insert(0, "0")
        self.discount_entry.pack(side="right", padx=5)
        self.discount_entry.bind("<KeyRelease>", self.update_total)
        
        # Currency change reflected here
        self.discount_label = tk.Label(total_frame, text=f"Discount Amt: -{CURRENCY_SYMBOL}0.00", font=("Arial", 14), fg="#e74c3c", bg="#ecf0f1", anchor="e")
        self.discount_label.pack(fill="x", padx=10, pady=2)
        
        # Currency change reflected here
        self.total_label = tk.Label(total_frame, text=f"Total: {CURRENCY_SYMBOL}0.00", font=("Arial", 18, "bold"), bg="#ecf0f1", anchor="e")
        self.total_label.pack(fill="x", padx=10, pady=10)

        # Payment/Change Area
        payment_frame = tk.Frame(total_frame, bg="#ecf0f1")
        payment_frame.pack(fill="x", padx=10, pady=(10, 2)) # Add some padding

        tk.Label(payment_frame, text=f"Received {CURRENCY_SYMBOL}:", font=("Arial", 14), bg="#ecf0f1").pack(side="left")
        
        self.received_entry = ttk.Entry(payment_frame, font=("Arial", 14), width=10)
        self.received_entry.pack(side="right", padx=5)
        
        # Bind to update_change function
        self.received_entry.bind("<KeyRelease>", self.update_change)

        # Change Label
        self.change_label = tk.Label(total_frame, text=f"Change: {CURRENCY_SYMBOL}0.00", font=("Arial", 16, "bold"), fg="#008000", bg="#ecf0f1", anchor="e") # Green for change
        self.change_label.pack(fill="x", padx=10, pady=5)

        # Action Buttons
        button_frame = tk.Frame(actions_frame, bg="white")
        button_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        checkout_button = tk.Button(button_frame, text="Checkout", font=("Arial", 16, "bold"), bg="#2ecc71", fg="white", height=3, command=self.checkout)
        checkout_button.pack(fill="x", pady=10)
        
        clear_button = tk.Button(button_frame, text="Clear Cart", font=("Arial", 14), bg="#e74c3c", fg="white", height=2, command=self.clear_cart)
        clear_button.pack(fill="x", pady=10)

    def scan_item(self, event=None):
        """Adds unit-based items with a specified quantity to the cart."""
        barcode = self.barcode_entry.get()
        if not barcode:
            return

        # Validate quantity
        try:
            quantity_to_add = int(self.unit_quantity_entry.get())
            if quantity_to_add <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity. Must be a positive whole number.")
            self.barcode_entry.delete(0, 'end')
            return

        # Check if product exists
        if barcode not in self.products:
            messagebox.showerror("Error", "Product not found.")
            self.barcode_entry.delete(0, 'end')
            return

        product = self.products[barcode]
        unit_price = product['price']
        current_stock = self.inventory.get(barcode, {}).get('quantity', 0)
        cart_qty = self.cart.get(barcode, {}).get('quantity', 0)

        # Check stock availability
        if current_stock < (cart_qty + quantity_to_add):
            messagebox.showerror(
                "Error",
                f"Not enough '{product['name']}' in stock. Available: {current_stock - cart_qty:.0f} units."
            )
            self.barcode_entry.delete(0, 'end')
            return

        # Add or update item in cart
        if barcode in self.cart:
            self.cart[barcode]['quantity'] += float(quantity_to_add)
        else:
            self.cart[barcode] = {
                'name': product['name'],     # Product name stored here
                'unit_price': unit_price,
                'quantity': float(quantity_to_add),
                'is_weighted': False
            }

        # Update line total
        self.cart[barcode]['line_total'] = self.cart[barcode]['unit_price'] * self.cart[barcode]['quantity']

        # Update UI
        self.update_cart_display()
        self.update_total()
        self.barcode_entry.delete(0, 'end')
        self.unit_quantity_entry.delete(0, 'end')
        self.unit_quantity_entry.insert(0, "1")

    def add_weighted_item(self):
        """Adds a weighted item to the cart, aggregating by weight."""
        barcode = self.weight_barcode_entry.get()
        try:
            weight = float(self.weight_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid weight. Please enter a number."); return

        if not barcode.startswith("W-"):
            messagebox.showerror("Error", "This is not a weighted item barcode (must start with 'W-')."); return

        if barcode not in self.products:
            messagebox.showerror("Error", "Weighted product not found."); return

        if weight <= 0:
            messagebox.showerror("Error", "Weight must be positive."); return
            
        product = self.products[barcode]
        unit_price = product['price']
        current_stock = self.inventory.get(barcode, {}).get('quantity', 0)
        cart_qty = self.cart.get(barcode, {}).get('quantity', 0)
        
        if current_stock < (cart_qty + weight):
            messagebox.showerror("Error", f"Not enough {product['name']} in stock. Available: {current_stock - cart_qty:.2f} kg."); return

        line_price = unit_price * weight
        
        if barcode in self.cart:
            self.cart[barcode]['quantity'] += weight
            self.cart[barcode]['line_total'] += line_price
        else:
            self.cart[barcode] = {
                'name': product['name'],
                'unit_price': unit_price,
                'quantity': weight,
                'line_total': line_price,
                'is_weighted': True
            }
        
        self.update_cart_display()
        self.update_total()
        self.weight_barcode_entry.delete(0, 'end')
        self.weight_barcode_entry.insert(0, "W-")
        self.weight_entry.delete(0, 'end')

    def update_cart_display(self):
        """Refreshes the cart Listbox with aggregated items and quantities."""
        self.cart_list.delete(0, 'end')
        
        for barcode, item in self.cart.items():
            qty_display = f"{item['quantity']:.0f}" if not item['is_weighted'] else f"{item['quantity']:.2f} kg"
            name_display = item['name']
            qty_padded = f"{qty_display:<8}"
            
            # Currency change reflected here
            display_string = f"{qty_padded} {name_display:<30} {CURRENCY_SYMBOL}{item['line_total']:>8.2f}"
            self.cart_list.insert('end', display_string)

    def update_total(self, event=None):
        """Recalculates and updates the total labels, including discount."""
        
        self.subtotal = sum(item['line_total'] for item in self.cart.values())

        try:
            discount_percent = float(self.discount_entry.get())
            if not (0 <= discount_percent <= 100):
                self.discount_entry.delete(0, 'end')
                self.discount_entry.insert(0, "0")
                discount_percent = 0.0
        except ValueError:
            discount_percent = 0.0

        discount_amount = self.subtotal * (discount_percent / 100.0)
        
        self.final_total = self.subtotal - discount_amount
        
        # Currency change reflected here
        self.subtotal_label.config(text=f"Subtotal: {CURRENCY_SYMBOL}{self.subtotal:.2f}")
        self.discount_label.config(text=f"Discount Amt ({discount_percent:.0f}%): -{CURRENCY_SYMBOL}{discount_amount:.2f}")
        self.total_label.config(text=f"Total: {CURRENCY_SYMBOL}{self.final_total:.2f}")

        # Trigger change update whenever total is updated
        self.update_change()

    def update_change(self, event=None):
        """Calculates and displays the change due based on amount received."""
        try:
            received_amount = float(self.received_entry.get())
        except ValueError:
            received_amount = 0.0

        change = received_amount - self.final_total
        
        if change < 0 and received_amount > 0: # Only show as "due" if some payment was attempted
            # Not enough paid yet
            self.change_label.config(text=f"Amount Due: {CURRENCY_SYMBOL}{abs(change):.2f}", fg="#e74c3c") # Red
        elif change < 0 and received_amount == 0.0:
            # Default state before any payment
            self.change_label.config(text=f"Change: {CURRENCY_SYMBOL}0.00", fg="#008000") # Green
        else:
            # Paid enough, show change
            self.change_label.config(text=f"Change: {CURRENCY_SYMBOL}{change:.2f}", fg="#008000") # Green

    def remove_selected_item(self):
        """Removes the selected item line from the cart."""
        selected_indices = self.cart_list.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select an item to remove."); return
            
        selected_index = selected_indices[0]
        
        try:
            barcode_to_remove = list(self.cart.keys())[selected_index]
        except IndexError:
            messagebox.showerror("Error", "Invalid selection."); return
        
        item_name = self.cart[barcode_to_remove]['name']
        
        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove all {item_name} from the cart?"):
            del self.cart[barcode_to_remove]
            self.update_cart_display()
            self.update_total()

    def generate_receipt(self, final_total, discount_amount, discount_percent, received_amount, change_amount):
        """Generates a text receipt and saves it to a file."""
        
        if not os.path.exists(RECEIPT_FOLDER):
            os.makedirs(RECEIPT_FOLDER)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(RECEIPT_FOLDER, f"receipt_{timestamp}.txt")

        receipt_lines = []
        shop_name = self.controller.shop_name_var.get().upper()
        
        receipt_lines.append("=" * 50)
        receipt_lines.append(f" {shop_name:^38}") 
        receipt_lines.append("=" * 50)
        receipt_lines.append(f"Date/Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        receipt_lines.append("-" * 50)
        
        receipt_lines.append(f"{'QTY':<8}{'ITEM':<24}{'AMOUNT':>8}")
        receipt_lines.append("-" * 50)
        
        for item in self.cart.values():
            qty_display = f"{item['quantity']:.0f}" if not item['is_weighted'] else f"{item['quantity']:.2f} kg"
            # Currency change reflected here
            amount_display = f"{CURRENCY_SYMBOL}{item['line_total']:.2f}"
            line = f"{qty_display:<8}{item['name'][:24]:<24}{amount_display:>8}"
            receipt_lines.append(line)
            
        receipt_lines.append("-" * 50)
        
        # Currency change reflected here
        receipt_lines.append(f"{'Subtotal:':<30}{CURRENCY_SYMBOL}{self.subtotal:>8.2f}")
        receipt_lines.append(f"Discount ({discount_percent:.0f}%): -{CURRENCY_SYMBOL}{discount_amount:>8.2f}")
        receipt_lines.append(f"{'TOTAL:':<30}{CURRENCY_SYMBOL}{final_total:>8.2f}")
        
        # Add payment details to receipt
        receipt_lines.append("-" * 50)
        receipt_lines.append(f"{'Amount Paid:':<30}{CURRENCY_SYMBOL}{received_amount:>8.2f}")
        receipt_lines.append(f"{'Change Given:':<30}{CURRENCY_SYMBOL}{change_amount:>8.2f}")
        
        receipt_lines.append("=" * 50)
        receipt_lines.append("Thank you for shopping! Come Again!")
        # receipt_lines.append("\nThank you for shopping! Come Again!")
        receipt_lines.append("=" * 50)

        try:
            with open(filepath, 'w') as f:
                f.write('\n'.join(receipt_lines))
            return filepath
        except IOError:
            messagebox.showerror("Error", "Could not save receipt file.")
            return None

    def checkout(self):
        """Finalizes the sale and updates inventory and generates a receipt."""
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty."); return
            
        self.update_total() 
        discount_percent = float(self.discount_entry.get()) if self.discount_entry.get() else 0.0
        if not (0 <= discount_percent <= 100): discount_percent = 0.0

        discount_amount = self.subtotal * (discount_percent / 100.0)
        final_total = self.subtotal - discount_amount
        
        # Get Received and Change amounts
        try:
            received_amount = float(self.received_entry.get())
        except ValueError:
            received_amount = 0.0 # Default to 0 if not entered
            
        # Check if payment is sufficient
        if received_amount < final_total:
            messagebox.showerror("Error", f"Amount received ({CURRENCY_SYMBOL}{received_amount:.2f}) is less than the total due ({CURRENCY_SYMBOL}{final_total:.2f}).")
            return # Stop checkout
            
        change_amount = received_amount - final_total
        
        # Updated confirmation message
        confirmation_message = (
            f"Total (after discount) is {CURRENCY_SYMBOL}{final_total:.2f}.\n"
            f"Amount Received: {CURRENCY_SYMBOL}{received_amount:.2f}\n"
            f"Change to Give: {CURRENCY_SYMBOL}{change_amount:.2f}\n\n"
            "Proceed with checkout?"
        )
        if not messagebox.askyesno("Confirm Checkout", confirmation_message): return

        # --- NEW --- Log the sale to sales_log.json
        try:
            log_sale(self.cart)
        except Exception as e:
            messagebox.showerror("Error", f"Could not log sale data: {e}")
            # Don't stop the checkout, but warn the user
        # --- END NEW ---

        self.refresh_data() 
        
        for barcode, item in self.cart.items():
            quantity_sold = item['quantity'] 
            item_name = item['name']
            
            if barcode in self.inventory:
                self.inventory[barcode]['quantity'] -= quantity_sold
                if self.inventory[barcode]['quantity'] < 0:
                    messagebox.showwarning("Inventory Warning", f"Stock for {item_name} is now negative. Manual check required.")
            else:
                messagebox.showerror("Critical Error", f"{item_name} was sold but is not in inventory!")

        save_data(INVENTORY_DB, self.inventory)
        
        # After saving inventory, update the dot status immediately
        self.update_low_stock_dot() 
        
        # Pass new values to receipt generator
        filepath = self.generate_receipt(final_total, discount_amount, discount_percent, received_amount, change_amount)

        if filepath:
            messagebox.showinfo("Success", f"Checkout complete. Inventory updated. Receipt saved to:\n{filepath}")
        else:
            messagebox.showinfo("Success", "Checkout complete. Inventory updated.") 
            
        self.clear_cart()

    def clear_cart(self):
        """Clears the cart and resets totals."""
        self.cart = {}
        self.update_cart_display()
        
        self.discount_entry.delete(0, 'end')
        self.discount_entry.insert(0, "0")
        
        # Reset received and change fields
        self.received_entry.delete(0, 'end')
        self.change_label.config(text=f"Change: {CURRENCY_SYMBOL}0.00", fg="#008000") # Reset to default
        
        self.update_total() # This will reset subtotal, total, and call update_change


# --- Inventory Management Frame ---
class InventoryFrame(tk.Frame):
    """A screen for adding, editing, and viewing product inventory."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.create_widgets()
        self.refresh_data()

    def create_widgets(self):
        # --- Navigation ---
        nav_frame = tk.Frame(self, bg="#34495e")
        nav_frame.pack(side="top", fill="x")
        
        tk.Label(nav_frame, text="Inventory Management", font=("Arial", 16, "bold"),
                 fg="white", bg="#34495e").pack(side="left", padx=10, pady=10)
        
        # Navigation buttons
        tk.Button(nav_frame, text="Bill Screen", font=("Arial", 10),
                  command=lambda: self.controller.show_frame(POSFrame)).pack(side="right", padx=10, pady=10)
        tk.Button(nav_frame, text="Bill History", font=("Arial", 10),
                  command=lambda: self.controller.show_frame(BillHistoryFrame)).pack(side="right", padx=10, pady=10)
        tk.Button(nav_frame, text="Sales Analytics", font=("Arial", 10),
                  command=lambda: self.controller.show_frame(AnalyticsFrame)).pack(side="right", padx=10, pady=10)

        # --- Main Content Area ---
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # --- Left Side (Product Form) ---
        form_frame = tk.Frame(main_frame, bd=2, relief="groove")
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        tk.Label(form_frame, text="Product Details", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=10)

        # Labels
        tk.Label(form_frame, text="Barcode:", font=("Arial", 12)).grid(
            row=1, column=0, sticky="w", padx=10, pady=5)
        tk.Label(form_frame, text="Product Name:", font=("Arial", 12)).grid(
            row=2, column=0, sticky="w", padx=10, pady=5)
        tk.Label(form_frame, text=f"Price ({CURRENCY_SYMBOL}):", font=("Arial", 12)).grid(
            row=3, column=0, sticky="w", padx=10, pady=5)
        tk.Label(form_frame, text="Quantity:", font=("Arial", 12)).grid(
            row=4, column=0, sticky="w", padx=10, pady=5)
        
        # Entries
        self.barcode_entry = ttk.Entry(form_frame, font=("Arial", 12))
        self.barcode_entry.grid(row=1, column=1, padx=10, pady=5)

        # 🔹 Bind Enter key to auto-fill product details
        self.barcode_entry.bind("<Return>", self.auto_fill_product_details)
        
        self.name_entry = ttk.Entry(form_frame, font=("Arial", 12))
        self.name_entry.grid(row=2, column=1, padx=10, pady=5)
        
        self.price_entry = ttk.Entry(form_frame, font=("Arial", 12))
        self.price_entry.grid(row=3, column=1, padx=10, pady=5)
        
        self.quantity_entry = ttk.Entry(form_frame, font=("Arial", 12))
        self.quantity_entry.grid(row=4, column=1, padx=10, pady=5)
        
        # Note for weighted items
        tk.Label(form_frame, text="For weighted items, start Barcode with 'W-'\n"
                                  "(Price is per kg, Quantity is total kg in stock).",
                 font=("Arial", 9, "italic")).grid(row=5, column=0, columnspan=2, padx=10, pady=10)
        
        # Buttons
        button_frame = tk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Add/Update Product",
                   command=self.add_update_product).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Product",
                   command=self.delete_product).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear Form",
                   command=self.clear_form).pack(side="left", padx=5)

        # --- Right Side (Inventory List) ---
        list_frame = tk.Frame(main_frame, bd=2, relief="groove")
        list_frame.grid(row=0, column=1, sticky="nsew")
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(list_frame, text="Current Inventory",
                 font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=10)

        self.inventory_list = tk.Listbox(list_frame, font=("Courier", 11))
        sb = tk.Scrollbar(list_frame, orient="vertical", command=self.inventory_list.yview)
        self.inventory_list.configure(yscrollcommand=sb.set)
        
        self.inventory_list.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=10)
        sb.grid(row=1, column=1, sticky="ns", padx=(0,10), pady=10)
        
        self.inventory_list.bind('<<ListboxSelect>>', self.load_selected_product)

    # 🔹 Auto-fill function
    def auto_fill_product_details(self, event=None):
        """Auto-fills product name, price, and quantity when a barcode is entered or scanned."""
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            return

        # Load data
        self.products = load_data(PRODUCTS_DB)
        self.inventory = load_data(INVENTORY_DB)

        # Check if product exists
        if barcode in self.products:
            product = self.products[barcode]
            inventory_item = self.inventory.get(barcode, {"quantity": 0})

            # Fill details
            self.name_entry.delete(0, 'end')
            self.name_entry.insert(0, product.get('name', ''))

            self.price_entry.delete(0, 'end')
            self.price_entry.insert(0, str(product.get('price', '')))

            self.quantity_entry.delete(0, 'end')
            self.quantity_entry.insert(0, str(inventory_item.get('quantity', 0)))
        else:
            # Clear fields for new products
            self.name_entry.delete(0, 'end')
            self.price_entry.delete(0, 'end')
            self.quantity_entry.delete(0, 'end')
            messagebox.showinfo("New Product", "This barcode is not in the system. You can add a new product.")

    def refresh_data(self):
        """Loads data, sorts by quantity, and updates listbox."""
        self.products = load_data(PRODUCTS_DB)
        self.inventory = load_data(INVENTORY_DB)
        
        inventory_items = []
        for barcode, product in self.products.items():
            quantity = self.inventory.get(barcode, {}).get('quantity', 0)
            price = product.get('price', 0.0)
            name = product.get('name', 'N/A')
            inventory_items.append((quantity, barcode, name, price))

        inventory_items.sort(key=lambda x: x[0]) 

        self.inventory_list.delete(0, 'end')
        self.inventory_list.insert('end', f"{'Barcode':<15} {'Name':<30} {'Price (Rs.)':<10} {'Qty':<5}")
        self.inventory_list.insert('end', "-"*60)
        
        for quantity, barcode, name, price in inventory_items:
            list_string = f"{barcode:<15} {name:<30} {price:<10.2f} {quantity:<5}"
            self.inventory_list.insert('end', list_string)
            if quantity < LOW_STOCK_THRESHOLD:
                last_index = self.inventory_list.size() - 1
                self.inventory_list.itemconfig(last_index, {'fg': 'red'})

    # 🔹 Updated add/update method (adds quantity to current stock)
    def add_update_product(self):
        """Adds a new product or updates an existing one (adds to current quantity if exists)."""
        barcode = self.barcode_entry.get().strip()
        name = self.name_entry.get().strip()
        try:
            price = float(self.price_entry.get())
            quantity_to_add = float(self.quantity_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Price and Quantity must be numbers.")
            return

        if not barcode or not name:
            messagebox.showerror("Error", "Barcode and Name are required.")
            return

        # Load existing quantities
        current_quantity = self.inventory.get(barcode, {}).get("quantity", 0)
        new_quantity = current_quantity + quantity_to_add

        # Save/Update product info
        self.products[barcode] = {"name": name, "price": price}
        self.inventory[barcode] = {"quantity": new_quantity}
        
        save_data(PRODUCTS_DB, self.products)
        save_data(INVENTORY_DB, self.inventory)
        
        messagebox.showinfo("Success", f"Product '{name}' updated. Total Quantity: {new_quantity}")
        self.clear_form()
        self.refresh_data()
        
        self.controller.frames[POSFrame].update_low_stock_dot() 

    def load_selected_product(self, event=None):
        """Loads selected product data from the list into the form."""
        selected_indices = self.inventory_list.curselection()
        if not selected_indices:
            return
            
        selected_line = self.inventory_list.get(selected_indices[0])
        try:
            if selected_indices[0] <= 1:
                return
            barcode = selected_line.split()[0]
        except (IndexError, AttributeError):
            return 
        
        if barcode not in self.products:
            return

        product = self.products[barcode]
        inventory = self.inventory.get(barcode, {"quantity": 0})
        
        self.clear_form()
        self.barcode_entry.insert(0, barcode)
        self.name_entry.insert(0, product['name'])
        self.price_entry.insert(0, str(product['price']))
        self.quantity_entry.insert(0, str(inventory['quantity']))
        
    def delete_product(self):
        """Deletes a product from the system."""
        barcode = self.barcode_entry.get()
        if not barcode:
            messagebox.showerror("Error", "Load a product or enter a barcode to delete.")
            return
            
        if barcode not in self.products:
            messagebox.showerror("Error", "Product not found.")
            return

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete product {barcode}? This cannot be undone."):
            return

        if barcode in self.products:
            del self.products[barcode]
        if barcode in self.inventory:
            del self.inventory[barcode]
            
        save_data(PRODUCTS_DB, self.products)
        save_data(INVENTORY_DB, self.inventory)
        
        messagebox.showinfo("Success", f"Product {barcode} deleted.")
        self.clear_form()
        self.refresh_data()
        self.controller.frames[POSFrame].update_low_stock_dot() 

    def clear_form(self):
        """Clears all entry fields in the form."""
        self.barcode_entry.delete(0, 'end')
        self.name_entry.delete(0, 'end')
        self.price_entry.delete(0, 'end')
        self.quantity_entry.delete(0, 'end')

# --- Bill History Frame ---

class BillHistoryFrame(tk.Frame):
    """A screen for viewing past receipts."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.create_widgets()
        
    def create_widgets(self):
        # --- Navigation ---
        nav_frame = tk.Frame(self, bg="#34495e")
        nav_frame.pack(side="top", fill="x")
        
        tk.Label(nav_frame, text="Bill History", font=("Arial", 16, "bold"), fg="white", bg="#34495e").pack(side="left", padx=10, pady=10)
        
        # --- MODIFIED --- Added Analytics button
        tk.Button(nav_frame, text="Bill Screen", font=("Arial", 10), command=lambda: self.controller.show_frame(POSFrame)).pack(side="right", padx=10, pady=10)
        tk.Button(nav_frame, text="Inventory", font=("Arial", 10), command=lambda: self.controller.show_frame(InventoryFrame)).pack(side="right", padx=10, pady=10)
        tk.Button(nav_frame, text="Sales Analytics", font=("Arial", 10), command=lambda: self.controller.show_frame(AnalyticsFrame)).pack(side="right", padx=10, pady=10)
        
        # --- Main Content Area ---
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        main_frame.grid_columnconfigure(0, weight=1) # List of bills
        main_frame.grid_columnconfigure(1, weight=2) # Bill content
        main_frame.grid_rowconfigure(0, weight=1)

        # --- Left Side (Bill List) ---
        list_frame = tk.Frame(main_frame, bd=2, relief="groove")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(list_frame, text="Saved Bills (Newest First)", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.bill_list = tk.Listbox(list_frame, font=("Courier", 11))
        sb_list = tk.Scrollbar(list_frame, orient="vertical", command=self.bill_list.yview)
        self.bill_list.configure(yscrollcommand=sb_list.set)
        
        self.bill_list.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=10)
        sb_list.grid(row=1, column=1, sticky="ns", padx=(0,10), pady=10)
        
        self.bill_list.bind('<<ListboxSelect>>', self.load_selected_bill)

        # --- Right Side (Bill Content) ---
        content_frame = tk.Frame(main_frame, bd=2, relief="groove")
        content_frame.grid(row=0, column=1, sticky="nsew")
        content_frame.grid_rowconfigure(1, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(content_frame, text="Bill Content", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.bill_content_text = tk.Text(content_frame, font=("Courier", 11), wrap="word", state="disabled")
        sb_content = tk.Scrollbar(content_frame, orient="vertical", command=self.bill_content_text.yview)
        self.bill_content_text.configure(yscrollcommand=sb_content.set)
        
        self.bill_content_text.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=10)
        sb_content.grid(row=1, column=1, sticky="ns", padx=(0,10), pady=10)

    def refresh_data(self):
        """Loads the list of saved receipts."""
        self.bill_list.delete(0, 'end')
        
        # Clear the text box
        self.bill_content_text.config(state="normal")
        self.bill_content_text.delete(1.0, 'end')
        
        if not os.path.exists(RECEIPT_FOLDER):
            self.bill_content_text.insert('end', f"Error: Receipt folder '{RECEIPT_FOLDER}' not found.")
            self.bill_content_text.config(state="disabled")
            return

        try:
            # Get all files and filter for .txt
            files = os.listdir(RECEIPT_FOLDER)
            txt_files = [f for f in files if f.endswith('.txt')]
            
            # Sort by name (which is timestamp) in reverse order
            txt_files.sort(reverse=True)
            
            if not txt_files:
                self.bill_content_text.insert('end', "No saved bills found.")
            else:
                self.bill_content_text.insert('end', "Select a bill from the left to view its details.")
                for f in txt_files:
                    self.bill_list.insert('end', f)
                    
        except Exception as e:
            self.bill_content_text.insert('end', f"An error occurred while loading bills:\n{e}")
        
        self.bill_content_text.config(state="disabled")

    def load_selected_bill(self, event=None):
        """Loads the content of the selected receipt into the text box."""
        selected_indices = self.bill_list.curselection()
        if not selected_indices: return
            
        filename = self.bill_list.get(selected_indices[0])
        filepath = os.path.join(RECEIPT_FOLDER, filename)
        
        self.bill_content_text.config(state="normal")
        self.bill_content_text.delete(1.0, 'end')
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            self.bill_content_text.insert('end', content)
        except Exception as e:
            self.bill_content_text.insert('end', f"Error reading file {filename}:\n{e}")
            
        self.bill_content_text.config(state="disabled")


# --- NEW --- Sales Analytics Frame ---

class AnalyticsFrame(tk.Frame):
    """A screen for viewing product sales charts."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Set up the figure and axis for matplotlib
        # We create them once and clear/redraw them in refresh_data
        self.fig = plt.Figure(figsize=(10, 6), dpi=100, facecolor='#f0f0f0')
        self.ax = self.fig.add_subplot(111)
        
        self.create_widgets()
        
    def create_widgets(self):
        # --- Navigation ---
        nav_frame = tk.Frame(self, bg="#34495e")
        nav_frame.pack(side="top", fill="x")
        
        tk.Label(nav_frame, text="Sales Analytics", font=("Arial", 16, "bold"), fg="white", bg="#34495e").pack(side="left", padx=10, pady=10)
        
        tk.Button(nav_frame, text="Bill Screen", font=("Arial", 10), command=lambda: self.controller.show_frame(POSFrame)).pack(side="right", padx=10, pady=10)
        tk.Button(nav_frame, text="Inventory", font=("Arial", 10), command=lambda: self.controller.show_frame(InventoryFrame)).pack(side="right", padx=10, pady=10)
        tk.Button(nav_frame, text="Bill History", font=("Arial", 10), command=lambda: self.controller.show_frame(BillHistoryFrame)).pack(side="right", padx=10, pady=10)
       

        # --- Main Content Area (Chart) ---
        main_frame = tk.Frame(self, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create the Tkinter canvas to embed the matplotlib chart
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Label to show if no data is available
        self.no_data_label = tk.Label(main_frame, text="No sales data found.", font=("Arial", 18, "bold"), bg="#f0f0f0")
        # This label will be shown/hidden in refresh_data


    def refresh_data(self):
        """Loads sales data, processes it, and draws the bar chart."""
        
        # 1. Load the sales data
        sales = load_data(SALES_LOG_DB)
        
        # 2. Check if data exists
        if not sales or not isinstance(sales, list):
            self.ax.clear() # Clear any old chart
            self.canvas.draw()
            # Show the 'no data' label
            self.no_data_label.pack(side=tk.TOP, pady=20)
            return
        
        # If data *is* found, hide the 'no data' label
        self.no_data_label.pack_forget()

        # 3. Process the data: Aggregate quantities by product name
        product_sales = {} # e.g., {'Apples': 10, 'Oranges': 5}
        
        for sale in sales:
            name = sale.get('name', 'Unknown Product')
            quantity = sale.get('quantity', 0)
            
            # Aggregate the quantity
            product_sales[name] = product_sales.get(name, 0) + quantity

        if not product_sales:
             self.ax.clear()
             self.canvas.draw()
             self.no_data_label.pack(side=tk.TOP, pady=20)
             return
             
        # 4. Sort the data (most to least selling) as requested
        # This gives a list of tuples: [('Apples', 10), ('Oranges', 5)]
        sorted_sales = sorted(product_sales.items(), key=lambda item: item[1], reverse=True)
        
        # 5. Unzip the sorted data into two lists for plotting
        products = [item[0] for item in sorted_sales]
        quantities = [item[1] for item in sorted_sales]
        
        # 6. Draw the chart
        self.ax.clear() # Clear the previous plot
        
        self.ax.bar(products, quantities, color='skyblue')
        
        # Set titles and labels
        self.ax.set_title('Product Sales Analytics (Most to Least Sold)', fontsize=16)
        self.ax.set_ylabel('Total Quantity Sold', fontsize=12)
        self.ax.set_xlabel('Product', fontsize=12)
        
        # Set background color
        self.ax.set_facecolor('#f0f0f0')
        
        # Rotate x-axis labels for better readability if they overlap
        self.fig.autofmt_xdate(rotation=45) 
        self.fig.tight_layout() # Adjust plot to fit
        
        # Redraw the canvas
        self.canvas.draw()

# --- Run the Application ---

if __name__ == "__main__":
    app = GroceryPOSApp()
    app.mainloop()
