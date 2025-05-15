import pyvisa
import tkinter as tk
from tkinter import ttk, messagebox

def scan_gpib_devices():
    output_box.delete(0, tk.END)
    try:
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        gpib_devices = [res for res in resources if "GPIB" in res]

        if not gpib_devices:
            output_box.insert(tk.END, "No GPIB devices found.")
            return

        for device in gpib_devices:
            try:
                inst = rm.open_resource(device)
                idn = inst.query("*IDN?")
                output_box.insert(tk.END, f"{device} -> {idn.strip()}")
            except Exception as e:
                output_box.insert(tk.END, f"{device} -> Error: {e}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Create the GUI
root = tk.Tk()
root.title("GPIB Device Scanner")
window_width = 400
window_height = 300  # Not strictly needed unless you want to fix the size

screen_width = root.winfo_screenwidth()

x=650#(screen_width // 2) - (window_width // 2)
y = 50  # Distance from the top of the screen

root.geometry(f"{window_width}x{window_height}+{x}+{y}")


frame = ttk.Frame(root, padding=10)
frame.grid()

ttk.Label(frame, text="Detected GPIB Devices:").grid(row=0, column=0, sticky=tk.W)

output_box = tk.Listbox(frame, width=80, height=10)
output_box.grid(row=1, column=0, padx=5, pady=5)

scan_button = ttk.Button(frame, text="Scan GPIB Devices", command=scan_gpib_devices)
scan_button.grid(row=2, column=0, pady=10)

root.mainloop()
