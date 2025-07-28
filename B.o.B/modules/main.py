from tkinter import messagebox
import customtkinter as ctk
import subprocess
import sys
import os

sys.stderr = open(os.devnull, "w")


def tier_clicked():
    try:
        process = subprocess.Popen(["python", "tier_impact_v2.py"])
        root.destroy()
        process.wait()
        messagebox.showinfo("Process Finished", "Tier Impact has been created")
    except FileNotFoundError:
        messagebox.showerror("File Not Found", "tier_impact_v2.py was not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def bg_clicked():
    try:
        process = subprocess.Popen(["python", "bg_impact_v2.py"])
        root.destroy()
        process.wait()
        messagebox.showinfo("Process Finished", "B/G Impact has been created")
    except FileNotFoundError:
        messagebox.showerror("File Not Found", "bg_impact_v2.py was not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def data_clicked():
    try:
        process = subprocess.Popen(["python", "data.py"])
        root.destroy()
        process.wait()
        messagebox.showinfo("Process Finished", "Only the data has been created")
    except FileNotFoundError:
        messagebox.showerror("File Not Found", "data.py was not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def bob_clicked():
    try:
        process = subprocess.Popen(["python", "bob.py"])
        root.destroy()
        process.wait()
    except FileNotFoundError:
        messagebox.showerror("File Not Found", "bob.py was not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def main():
    global root
    root = ctk.CTk()
    root.title("Member Impact")
    root.configure(fg_color="#333F48")

    text_block = """
    1. Check that all files required by the program are not currently in use (open).

    2. Ensure that the sheet name for the file with the main data is either 'Claims Table' or 'Sheet1'.

    3. If not using the repricing template, make sure the headers are formatted as follows:

     NDC  |  DATEFILLED  |  MemberID  |  FormularyTier  |  Rxs  |  Logic


    4. Be sure to follow the notes pop-up instructions.

    """

    warning_label = ctk.CTkLabel(
        root,
        text="Preliminary Checks",
        font=("Oswald", 30, "bold"),
        text_color="#FFD578",
        fg_color="#333F48",
    )
    text_label = ctk.CTkLabel(
        root, text=text_block, font=("Oswald", 20, "bold"), fg_color="#333F48"
    )

    tier_button = ctk.CTkButton(
        root,
        text="Tier Disruption",
        command=tier_clicked,
        font=(None, 20, "bold"),
        fg_color="#00B0B9",
        width=200,
        height=50,
    )
    bg_button = ctk.CTkButton(
        root,
        text="B/G Disruption",
        command=bg_clicked,
        font=(None, 20, "bold"),
        fg_color="#00B0B9",
        width=200,
        height=50,
    )
    data_button = ctk.CTkButton(
        root,
        text="Disruption Data Only",
        command=data_clicked,
        font=(None, 20, "bold"),
        fg_color="#00B0B9",
        width=200,
        height=50,
    )
    bob_button = ctk.CTkButton(
        root,
        text="B.o.B Drug Lookup",
        command=bob_clicked,
        font=(None, 20, "bold"),
        fg_color="#00B0B9",
        width=200,
        height=50,
    )

    # Place buttons in the window
    warning_label.grid(row=0, column=0, columnspan=2, pady=10)
    text_label.grid(row=1, column=0, columnspan=2, pady=10, padx=5)
    tier_button.grid(row=2, column=0, pady=5, padx=5)
    bg_button.grid(row=2, column=1, pady=5, padx=5)
    data_button.grid(row=3, column=0, pady=20, padx=100)
    bob_button.grid(row=3, column=1, pady=20, padx=100)

    # Run the main event loop
    root.mainloop()


if __name__ == "__main__":
    main()
