"""JSON-based Log File Analyzer - a mini project using only the standard library."""
import json
import tkinter as tk
from collections import Counter
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

LEVELS = ["INFO", "WARNING", "ERROR", "DEBUG"]
KEYS = ["timestamp", "level", "service", "message"]
LEVEL_COLORS = {"INFO": "#3B82F6", "WARNING": "#F59E0B", "ERROR": "#EF4444", "DEBUG": "#8B5CF6"}
NAVY, BG, FONT = "#1F2A44", "#F4F6FA", "Segoe UI"
SAMPLE_MESSAGES = {
    "INFO": ["User logged in successfully", "Payment processed", "Email sent to customer"],
    "WARNING": ["High memory usage detected", "Slow response from database", "Retrying failed request"],
    "ERROR": ["Database connection failed", "Payment gateway timeout", "Unhandled exception in request"],
    "DEBUG": ["Cache lookup for session token", "Query plan generated", "Config file loaded"],
}


# Check one log entry and return a cleaned copy, or None if it is invalid.
def clean_entry(item):
    if not isinstance(item, dict) or not all(key in item for key in KEYS):
        return None
    level = str(item["level"]).upper()
    if level not in LEVELS:
        return None
    return {"timestamp": str(item["timestamp"]), "level": level,
            "service": str(item["service"]), "message": str(item["message"])}


# Parse a JSON array or JSON Lines text and return (entries, skipped_count).
def parse_log_text(text):
    items, skipped = [], 0
    try:
        data = json.loads(text)  # works for a JSON array (or a single object)
        items = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:  # not one JSON document, so try JSON Lines
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                skipped += 1
    entries = []
    for item in items:
        entry = clean_entry(item)
        if entry:
            entries.append(entry)
        else:
            skipped += 1
    return entries, skipped


# Count totals, levels, errors and the top 3 services.
def compute_summary(entries):
    level_counts = Counter(entry["level"] for entry in entries)
    service_counts = Counter(entry["service"] for entry in entries)
    return {"total": len(entries), "errors": level_counts.get("ERROR", 0),
            "levels": {level: level_counts.get(level, 0) for level in LEVELS},
            "top_services": service_counts.most_common(3)}


# Turn the summary into the text that is saved in report.txt.
def format_report(summary, source):
    lines = ["LOG ANALYSIS REPORT", "=" * 30, f"Source file   : {source}",
             f"Generated     : {datetime.now():%Y-%m-%d %H:%M:%S}", "",
             f"Total entries : {summary['total']}", f"Errors        : {summary['errors']}",
             "", "Entries per level:"]
    lines += [f"  {level:<8}: {count}" for level, count in summary["levels"].items()]
    lines += ["", "Top 3 services:"]
    lines += [f"  {i}. {name} ({count} logs)" for i, (name, count) in enumerate(summary["top_services"], 1)]
    return "\n".join(lines)


# Build a list of 20 sample log entries for the demo.
def make_sample_entries():
    pattern = ["INFO", "INFO", "DEBUG", "INFO", "WARNING", "INFO", "ERROR", "INFO", "DEBUG", "WARNING",
               "INFO", "ERROR", "INFO", "INFO", "WARNING", "ERROR", "DEBUG", "INFO", "ERROR", "INFO"]
    services = ["auth", "database", "payment", "api-gateway", "email", "auth", "database", "auth"]
    start = datetime(2026, 10, 13, 9, 0, 0)
    entries = []
    for i, level in enumerate(pattern):
        time = start + timedelta(minutes=i * 3)
        entries.append({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "level": level,
                        "service": services[i % len(services)], "message": SAMPLE_MESSAGES[level][i % 3]})
    return entries


# Draw a simple bar chart of the level counts on a Canvas.
def draw_chart(canvas, level_counts):
    canvas.delete("all")
    biggest = max(level_counts.values()) or 1  # avoid dividing by zero
    base_y = 125
    canvas.create_line(20, base_y, 360, base_y, fill="#BBBBBB")
    for i, level in enumerate(LEVELS):
        count = level_counts[level]
        x = 45 + i * 85
        height = (count / biggest) * 90
        canvas.create_rectangle(x, base_y - height, x + 50, base_y, fill=LEVEL_COLORS[level], outline="")
        canvas.create_text(x + 25, base_y - height - 10, text=str(count), font=(FONT, 10, "bold"))
        canvas.create_text(x + 25, base_y + 12, text=level, font=(FONT, 9), fill="#555555")


# Create a small card showing a title and a big number.
def make_card(parent, title, variable, color):
    card = tk.Frame(parent, bg=BG, padx=14, pady=4)
    card.pack(side="left", padx=(0, 10))
    tk.Label(card, text=title, bg=BG, fg="#666666", font=(FONT, 9)).pack(anchor="w")
    tk.Label(card, textvariable=variable, bg=BG, fg=color, font=(FONT, 18, "bold")).pack(anchor="w")


class LogAnalyzerApp:
    # Set up data, styles and every part of the window.
    def __init__(self, root):
        self.root = root
        self.entries, self.visible, self.skipped = [], [], 0
        self.source, self.sort_reverse = "No file loaded", False
        root.title("JSON Log File Analyzer")
        root.geometry("900x600")
        root.minsize(900, 600)
        root.configure(bg=BG)
        self.setup_styles()
        self.build_top_bar()
        self.build_filter_row()
        self.build_bottom()  # packed before the table so the table fills the leftover space
        self.build_table()
        self.update_summary()
        self.apply_filters()
        self.level_var.trace_add("write", self.apply_filters)  # live filtering
        self.search_var.trace_add("write", self.apply_filters)

    # Choose the theme and style the buttons and the table.
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Accent.TButton", background="#3B82F6", foreground="white",
                        font=(FONT, 10, "bold"), padding=(12, 6), borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#2563EB")])
        style.configure("Treeview", rowheight=24, font=(FONT, 9), fieldbackground="white")
        style.configure("Treeview.Heading", font=(FONT, 10, "bold"), background="#E5E9F2", foreground=NAVY)
        style.map("Treeview", background=[("selected", "#2F4B7C")], foreground=[("selected", "white")])

    # Build the dark top bar with the title and the three main buttons.
    def build_top_bar(self):
        bar = tk.Frame(self.root, bg=NAVY, padx=15, pady=10)
        bar.pack(fill="x")
        tk.Label(bar, text="Log Analyzer", bg=NAVY, fg="white", font=(FONT, 16, "bold")).pack(side="left")
        buttons = [("Open Log File", self.open_file), ("Load Sample Data", self.load_sample),
                   ("Export Report", self.export_report)]
        for text, command in reversed(buttons):
            ttk.Button(bar, text=text, style="Accent.TButton", command=command).pack(side="right", padx=4)

    # Build the row with the level dropdown, search box and info label.
    def build_filter_row(self):
        row = tk.Frame(self.root, bg=BG, padx=15, pady=8)
        row.pack(fill="x")
        self.level_var, self.search_var = tk.StringVar(value="ALL"), tk.StringVar()
        tk.Label(row, text="Level:", bg=BG, font=(FONT, 10)).pack(side="left")
        ttk.Combobox(row, textvariable=self.level_var, values=["ALL"] + LEVELS,
                     state="readonly", width=10).pack(side="left", padx=(5, 15))
        tk.Label(row, text="Search:", bg=BG, font=(FONT, 10)).pack(side="left")
        ttk.Entry(row, textvariable=self.search_var, width=28).pack(side="left", padx=5)
        ttk.Button(row, text="Clear Filters", command=self.clear_filters).pack(side="left", padx=10)
        self.info_label = tk.Label(row, bg=BG, fg="#555555", font=(FONT, 9))
        self.info_label.pack(side="right")

    # Build the table (Treeview) with a scrollbar and colored row tags.
    def build_table(self):
        frame = tk.Frame(self.root, bg=BG, padx=15)
        frame.pack(fill="both", expand=True)
        columns = ("timestamp", "level", "service", "message")
        widths = {"timestamp": 150, "level": 80, "service": 120, "message": 450}
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column in columns:
            self.tree.heading(column, text=column.title(), command=lambda c=column: self.sort_by_column(c))
            self.tree.column(column, width=widths[column], anchor="w")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_configure("ERROR", background="#FDE2E2")
        self.tree.tag_configure("WARNING", background="#FFF6D6")
        self.tree.bind("<Double-1>", self.show_details)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # Build the bottom area: summary cards on the left, bar chart on the right.
    def build_bottom(self):
        bottom = tk.Frame(self.root, bg=BG, padx=15, pady=10)
        bottom.pack(side="bottom", fill="x")
        summary = tk.LabelFrame(bottom, text=" Summary ", bg="white", fg=NAVY, font=(FONT, 10, "bold"), padx=10, pady=4)
        summary.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.total_var, self.error_var = tk.StringVar(value="0"), tk.StringVar(value="0")
        self.levels_var, self.services_var = tk.StringVar(), tk.StringVar()
        cards = tk.Frame(summary, bg="white")
        cards.pack(fill="x")
        make_card(cards, "Total Entries", self.total_var, NAVY)
        make_card(cards, "Errors", self.error_var, LEVEL_COLORS["ERROR"])
        tk.Label(summary, textvariable=self.levels_var, bg="white", font=(FONT, 9, "bold"), anchor="w").pack(fill="x", pady=4)
        tk.Label(summary, textvariable=self.services_var, bg="white", fg="#333333", font=(FONT, 9),
                 justify="left", anchor="w").pack(fill="x")
        chart = tk.LabelFrame(bottom, text=" Logs per Level ", bg="white", fg=NAVY, font=(FONT, 10, "bold"), padx=6, pady=4)
        chart.pack(side="left", fill="both")
        self.canvas = tk.Canvas(chart, width=380, height=150, bg="white", highlightthickness=0)
        self.canvas.pack()

    # Ask the user for a file and load it.
    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Log files", "*.json *.log"), ("All files", "*.*")])
        if path:
            self.load_file(path)

    # Read a log file, parse it and refresh the whole window.
    def load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                entries, skipped = parse_log_text(file.read())
        except Exception as error:
            messagebox.showerror("Error", f"Could not open the file:\n{error}")
            return
        if not entries:
            messagebox.showwarning("No valid logs", f"No valid log entries found.\nSkipped: {skipped}")
            return
        self.entries, self.skipped = entries, skipped
        self.source = path.replace("\\", "/").split("/")[-1]
        self.clear_filters()
        self.update_summary()
        self.apply_filters()
        if skipped:
            messagebox.showinfo("Loaded with warnings", f"Loaded {len(entries)} entries.\nSkipped {skipped} bad line(s).")

    # Save 20 sample entries to sample_logs.json and load that file.
    def load_sample(self):
        try:
            with open("sample_logs.json", "w", encoding="utf-8") as file:
                json.dump(make_sample_entries(), file, indent=2)
        except OSError as error:
            messagebox.showerror("Error", f"Could not create the sample file:\n{error}")
            return
        self.load_file("sample_logs.json")

    # Keep only the entries that match the chosen level and keyword.
    def apply_filters(self, *args):
        level = self.level_var.get()
        keyword = self.search_var.get().strip().lower()
        self.visible = [e for e in self.entries
                        if (level == "ALL" or e["level"] == level) and keyword in " ".join(e.values()).lower()]
        self.fill_table()

    # Reset the dropdown and the search box.
    def clear_filters(self):
        self.level_var.set("ALL")
        self.search_var.set("")

    # Redraw the table rows and the info label.
    def fill_table(self):
        self.tree.delete(*self.tree.get_children())
        for e in self.visible:
            self.tree.insert("", "end", values=(e["timestamp"], e["level"], e["service"], e["message"]), tags=(e["level"],))
        self.info_label.config(text=f"{self.source}  |  Showing {len(self.visible)} of {len(self.entries)}  |  Skipped: {self.skipped}")

    # Sort the visible rows when a column heading is clicked.
    def sort_by_column(self, column):
        self.sort_reverse = not self.sort_reverse
        self.visible.sort(key=lambda e: e[column].lower(), reverse=self.sort_reverse)
        self.fill_table()

    # Show the full details of a row when it is double-clicked.
    def show_details(self, event):
        selected = self.tree.selection()
        if selected:
            time, level, service, message = self.tree.item(selected[0], "values")
            messagebox.showinfo("Log Details", f"Time: {time}\nLevel: {level}\nService: {service}\n\n{message}")

    # Refresh the summary cards, text and the bar chart.
    def update_summary(self):
        summary = compute_summary(self.entries)
        self.total_var.set(str(summary["total"]))
        self.error_var.set(str(summary["errors"]))
        self.levels_var.set("   ".join(f"{level}: {count}" for level, count in summary["levels"].items()))
        top = [f"  {i}. {name}  ({count} logs)" for i, (name, count) in enumerate(summary["top_services"], 1)]
        self.services_var.set("Top 3 Services\n" + ("\n".join(top) if top else "  No data"))
        draw_chart(self.canvas, summary["levels"])

    # Save the summary to report.txt.
    def export_report(self):
        if not self.entries:
            messagebox.showwarning("Nothing to export", "Load a log file first.")
            return
        try:
            with open("report.txt", "w", encoding="utf-8") as file:
                file.write(format_report(compute_summary(self.entries), self.source))
            messagebox.showinfo("Report saved", "Summary saved to report.txt")
        except OSError as error:
            messagebox.showerror("Error", f"Could not save the report:\n{error}")


if __name__ == "__main__":
    window = tk.Tk()
    LogAnalyzerApp(window)
    window.mainloop()