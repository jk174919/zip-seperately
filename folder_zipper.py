Attempting to perform the InitializeDefaultDrives operation on the 'FileSystem' provider failed.
"""FolderZipTool: create one ZIP archive for each selected folder."""

from __future__ import annotations

import os
import queue
import threading
import zipfile
from pathlib import Path
from tkinter import END, Tk, filedialog, messagebox, ttk


class FolderZipApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("FolderZipTool")
        self.root.geometry("760x560")
        self.root.minsize(650, 460)
        self.folders: list[Path] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        outer = ttk.Frame(root, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="FolderZipTool", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Select folders and create a separate ZIP archive for each one.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 14))

        folder_bar = ttk.Frame(outer)
        folder_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(folder_bar, text="Folders to ZIP", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.add_button = ttk.Button(folder_bar, text="＋ Add folder", command=self.add_folder)
        self.add_button.pack(side="right")

        list_frame = ttk.Frame(outer)
        list_frame.pack(fill="both", expand=True)
        self.folder_list = __import__("tkinter").Listbox(
            list_frame, selectmode="extended", font=("Segoe UI", 10),
            relief="solid", borderwidth=1, activestyle="dotbox",
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.folder_list.yview)
        self.folder_list.configure(yscrollcommand=scrollbar.set)
        self.folder_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        list_actions = ttk.Frame(outer)
        list_actions.pack(fill="x", pady=(6, 16))
        ttk.Button(list_actions, text="Remove selected", command=self.remove_selected).pack(side="left")
        ttk.Button(list_actions, text="Clear list", command=self.clear_list).pack(side="left", padx=(8, 0))

        ttk.Label(outer, text="Save ZIP files in", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        destination_row = ttk.Frame(outer)
        destination_row.pack(fill="x", pady=(6, 14))
        self.destination = __import__("tkinter").StringVar()
        ttk.Entry(destination_row, textvariable=self.destination).pack(side="left", fill="x", expand=True)
        ttk.Button(destination_row, text="Browse…", command=self.choose_destination).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        self.status = __import__("tkinter").StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(6, 8))

        footer = ttk.Frame(outer)
        footer.pack(fill="x")
        self.zip_button = ttk.Button(footer, text="Create ZIP files", command=self.start_zip, style="Accent.TButton")
        self.zip_button.pack(side="right")
        self.root.after(100, self.check_events)

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a folder to ZIP", mustexist=True)
        if folder:
            path = Path(folder).resolve()
            if path not in self.folders:
                self.folders.append(path)
                self.folder_list.insert(END, str(path))
            else:
                self.status.set(f"Already added: {path.name}")

    def remove_selected(self) -> None:
        for index in reversed(self.folder_list.curselection()):
            self.folder_list.delete(index)
            del self.folders[index]

    def clear_list(self) -> None:
        self.folders.clear()
        self.folder_list.delete(0, END)

    def choose_destination(self) -> None:
        folder = filedialog.askdirectory(title="Choose where ZIP files will be saved", mustexist=True)
        if folder:
            self.destination.set(folder)

    def start_zip(self) -> None:
        if not self.folders:
            messagebox.showinfo("Choose folders", "Add at least one folder before creating ZIP files.")
            return
        destination = Path(self.destination.get()).expanduser() if self.destination.get().strip() else None
        if destination is None or not destination.is_dir():
            messagebox.showinfo("Choose a save location", "Choose an existing folder for the ZIP files.")
            return
        folders = list(self.folders)
        self.zip_button.configure(state="disabled")
        self.add_button.configure(state="disabled")
        self.progress.configure(maximum=len(folders), value=0)
        self.status.set("Starting…")
        threading.Thread(target=self.zip_folders, args=(folders, destination), daemon=True).start()

    def zip_folders(self, folders: list[Path], destination: Path) -> None:
        used_names: set[str] = set()
        completed = 0
        errors: list[str] = []
        for folder in folders:
            name = folder.name or folder.drive.rstrip("\\:") or "folder"
            archive_name = f"{name}.zip"
            number = 2
            while archive_name.casefold() in used_names:
                archive_name = f"{name} ({number}).zip"
                number += 1
            used_names.add(archive_name.casefold())
            target = destination / archive_name
            try:
                with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
                    for current, dirnames, filenames in os.walk(folder, followlinks=False):
                        current_path = Path(current)
                        dirnames[:] = [d for d in dirnames if not (current_path / d).is_symlink()]
                        for filename in filenames:
                            source = current_path / filename
                            if source.is_symlink() or not source.is_file():
                                continue
                            archive.write(source, source.relative_to(folder.parent))
                completed += 1
                self.events.put(("progress", (completed, len(folders), f"Created {archive_name}")))
            except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                errors.append(f"{folder.name}: {exc}")
                self.events.put(("progress", (completed + len(errors), len(folders), f"Could not ZIP {folder.name}")))
        self.events.put(("done", (completed, errors, destination)))

    def check_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    current, total, label = payload  # type: ignore[misc]
                    self.progress.configure(value=current)
                    self.status.set(f"{label} ({current}/{total})")
                elif kind == "done":
                    completed, errors, destination = payload  # type: ignore[misc]
                    self.zip_button.configure(state="normal")
                    self.add_button.configure(state="normal")
                    self.status.set(f"Finished: {completed} ZIP file(s) created")
                    if errors:
                        messagebox.showwarning(
                            "Finished with errors",
                            f"Created {completed} ZIP file(s). These folders could not be zipped:\n\n" + "\n".join(errors),
                        )
                    else:
                        messagebox.showinfo("ZIP files created", f"Created {completed} ZIP file(s) in:\n{destination}")
        except queue.Empty:
            pass
        self.root.after(100, self.check_events)


def main() -> None:
    root = Tk()
    FolderZipApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

