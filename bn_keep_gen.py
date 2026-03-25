import tkinter as tk
from tkinter import messagebox
import os

class KeepGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("BN Keep Generator")
        self.root.geometry("550x450")
        
        # Header
        tk.Label(root, text="BN EASY PRUNER - Coordinate Generator", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(root, text="Enter ranges to PRESERVE. (Empty rows will be ignored)").pack()

        self.zones = []
        # English labels for global compatibility
        labels = ["Base", "Refugee Center", "Commune / Other"]
        
        frame = tk.Frame(root)
        frame.pack(pady=10, padx=20)

        for label in labels:
            row = tk.LabelFrame(frame, text=f" {label} ", padx=10, pady=5)
            row.pack(fill="x", pady=5)
            
            # Top-Left (Min)
            tk.Label(row, text="Top-Left X:").grid(row=0, column=0)
            tx = tk.Entry(row, width=8); tx.grid(row=0, column=1, padx=5)
            tk.Label(row, text="Y:").grid(row=0, column=2)
            ty = tk.Entry(row, width=8); ty.grid(row=0, column=3, padx=5)
            
            # Bottom-Right (Max)
            tk.Label(row, text="Bottom-Right X:").grid(row=1, column=0)
            bx = tk.Entry(row, width=8); bx.grid(row=1, column=1, padx=5)
            tk.Label(row, text="Y:").grid(row=1, column=2)
            by = tk.Entry(row, width=8); by.grid(row=1, column=3, padx=5)
            
            self.zones.append({'tx':tx, 'ty':ty, 'bx':bx, 'by':by})

        # Process Button
        self.btn = tk.Button(root, text="GENERATE KEEP.TXT & START PRUNER", 
                             command=self.save_and_exit, bg="#1976D2", fg="white", font=("Arial", 10, "bold"), pady=10)
        self.btn.pack(fill="x", padx=50, pady=20)

    def save_and_exit(self):
        keep_list = []
        z = 0 # Default Z-level
        try:
            for zone in self.zones:
                if not zone['tx'].get().strip(): continue
                
                # Get coordinates
                x1, y1 = int(zone['tx'].get()), int(zone['ty'].get())
                x2 = int(zone['bx'].get()) if zone['bx'].get().strip() else x1
                y2 = int(zone['by'].get()) if zone['by'].get().strip() else y1
                
                # Range logic from generate_keep.py (includes the end point)
                x_start, x_end = min(x1, x2), max(x1, x2)
                y_start, y_end = min(y1, y2), max(y1, y2)
                
                for x in range(x_start, x_end + 1):
                    for y in range(y_start, y_end + 1):
                        keep_list.append(f"{x}.{y}.{z}")

            if not keep_list:
                messagebox.showwarning("Warning", "No coordinates entered.")
                return

            # Save to keep.txt
            with open("keep.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(keep_list))
            
            # Close GUI to proceed to the next step in Batch file
            self.root.destroy()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers only.")

if __name__ == "__main__":
    root = tk.Tk()
    KeepGenerator(root)
    root.mainloop()