"""Build six-band pre/post stacks and a six-component PCA GeoTIFF per area."""

from __future__ import annotations

import math
import queue
import re
import threading
from pathlib import Path
from tkinter import END, Tk, filedialog, messagebox, ttk

import numpy as np
import rasterio


RASTER_EXTENSIONS = {".tif", ".tiff", ".img", ".vrt"}
BAND_LABELS = ("B2", "B3", "B4")
NODATA = -9999.0


class ProcessingError(Exception):
    pass


def find_area_raster(area_folder: Path) -> Path:
    candidates = sorted(
        (p for p in area_folder.rglob("*") if p.is_file() and p.suffix.lower() in RASTER_EXTENSIONS),
        key=lambda p: str(p).casefold(),
    )
    if len(candidates) != 1:
        if not candidates:
            raise ProcessingError("No GeoTIFF/IMG/VRT raster found in this area folder.")
        raise ProcessingError(f"Found {len(candidates)} rasters; each area folder must contain exactly one image.")
    return candidates[0]


def validate_band_order(dataset: rasterio.io.DatasetReader, label: str) -> None:
    if dataset.count != 3:
        raise ProcessingError(f"{label} image has {dataset.count} bands; expected exactly 3 (B2, B3, B4).")
    descriptions = dataset.descriptions
    present = [description.strip() if description else "" for description in descriptions]
    if not any(present):
        return  # The visible UI assumption asks the user to confirm B2, B3, B4 order.
    if not all(present):
        raise ProcessingError(f"{label} has incomplete band names; expected B2, B3, B4 in that order.")
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", value.casefold())
    aliases = [{"b2", "b02", "band2", "band02"}, {"b3", "b03", "band3", "band03"}, {"b4", "b04", "band4", "band04"}]
    if any(normalize(actual) not in expected for actual, expected in zip(present, aliases)):
        raise ProcessingError(f"{label} band names are {present}; expected B2, B3, B4 in that order.")


def validate_pair(pre: rasterio.io.DatasetReader, post: rasterio.io.DatasetReader) -> None:
    validate_band_order(pre, "Pre-image")
    validate_band_order(post, "Post-image")
    if pre.crs is None or post.crs is None:
        raise ProcessingError("Both images must have a defined coordinate reference system (CRS).")
    if pre.crs != post.crs:
        raise ProcessingError(f"CRS mismatch: pre is {pre.crs}, post is {post.crs}.")
    if (pre.width, pre.height) != (post.width, post.height):
        raise ProcessingError(
            f"Raster dimensions differ: pre is {pre.width}×{pre.height}, post is {post.width}×{post.height}."
        )
    if any(not math.isclose(a, b, rel_tol=0, abs_tol=1e-10) for a, b in zip(pre.res, post.res)):
        raise ProcessingError(f"Pixel resolutions differ: pre is {pre.res}, post is {post.res}.")

    pixel_tolerance = max(abs(pre.transform.a), abs(pre.transform.e), 1.0) * 1e-7
    pre_transform = tuple(pre.transform)[:6]
    post_transform = tuple(post.transform)[:6]
    if any(not math.isclose(a, b, rel_tol=0, abs_tol=pixel_tolerance) for a, b in zip(pre_transform, post_transform)):
        raise ProcessingError("The images are not on the same pixel grid (transform/origin differs).")
    bounds_a = (pre.bounds.left, pre.bounds.bottom, pre.bounds.right, pre.bounds.top)
    bounds_b = (post.bounds.left, post.bounds.bottom, post.bounds.right, post.bounds.top)
    if any(not math.isclose(a, b, rel_tol=0, abs_tol=pixel_tolerance) for a, b in zip(bounds_a, bounds_b)):
        raise ProcessingError("The images do not cover the same geographic extent.")


def aligned_windows(dataset: rasterio.io.DatasetReader):
    # Rasterio windows keep processing bounded in memory for large scenes.
    for _, window in dataset.block_windows(1):
        yield window


def stack_area(pre_path: Path, post_path: Path, stack_path: Path) -> int:
    with rasterio.open(pre_path) as pre, rasterio.open(post_path) as post:
        validate_pair(pre, post)
        profile = pre.profile.copy()
        profile.pop("photometric", None)
        profile.update(
            driver="GTiff", count=6, dtype="float32", nodata=NODATA,
            compress="deflate", predictor=3, BIGTIFF="IF_SAFER",
        )
        valid_count = 0
        with rasterio.open(stack_path, "w", **profile) as stack:
            for band, name in enumerate(("Pre_B2", "Pre_B3", "Pre_B4", "Post_B2", "Post_B3", "Post_B4"), 1):
                stack.set_band_description(band, name)
            for window in aligned_windows(pre):
                pre_data = pre.read((1, 2, 3), window=window).astype(np.float32, copy=False)
                post_data = post.read((1, 2, 3), window=window).astype(np.float32, copy=False)
                valid = np.all(pre.read_masks((1, 2, 3), window=window) > 0, axis=0)
                valid &= np.all(post.read_masks((1, 2, 3), window=window) > 0, axis=0)
                valid &= np.all(np.isfinite(pre_data), axis=0) & np.all(np.isfinite(post_data), axis=0)
                valid_count += int(valid.sum())
                combined = np.concatenate((pre_data, post_data), axis=0)
                combined[:, ~valid] = NODATA
                stack.write(combined, window=window)
    if valid_count < 2:
        raise ProcessingError("Fewer than two pixels have valid data in both images; PCA cannot be calculated.")
    return valid_count


def read_valid_samples(stack: rasterio.io.DatasetReader, window) -> tuple[np.ndarray, np.ndarray]:
    data = stack.read(tuple(range(1, 7)), window=window).astype(np.float64, copy=False)
    valid = np.all(stack.read_masks(tuple(range(1, 7)), window=window) > 0, axis=0)
    valid &= np.all(np.isfinite(data), axis=0)
    valid &= np.all(data != NODATA, axis=0)
    return data, valid


def create_pca(stack_path: Path, pca_path: Path) -> tuple[int, np.ndarray]:
    with rasterio.open(stack_path) as stack:
        count = 0
        total = np.zeros(6, dtype=np.float64)
        cross = np.zeros((6, 6), dtype=np.float64)
        for _, window in stack.block_windows(1):
            data, valid = read_valid_samples(stack, window)
            if not np.any(valid):
                continue
            samples = data[:, valid]
            count += samples.shape[1]
            total += samples.sum(axis=1)
            cross += samples @ samples.T
        if count < 2:
            raise ProcessingError("PCA needs at least two shared valid pixels.")
        mean = total / count
        covariance = (cross - count * np.outer(mean, mean)) / (count - 1)
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = np.maximum(eigenvalues[order], 0.0)
        eigenvectors = eigenvectors[:, order]

        # PCA axes have arbitrary signs. Make output reproducible by making the
        # largest-magnitude loading in each component positive.
        for component in range(6):
            pivot = int(np.argmax(np.abs(eigenvectors[:, component])))
            if eigenvectors[pivot, component] < 0:
                eigenvectors[:, component] *= -1

        profile = stack.profile.copy()
        profile.update(count=6, dtype="float32", nodata=NODATA, compress="deflate", predictor=3, BIGTIFF="IF_SAFER")
        with rasterio.open(pca_path, "w", **profile) as output:
            for component in range(6):
                output.set_band_description(component + 1, f"PC{component + 1}")
            total_variance = float(eigenvalues.sum())
            output.update_tags(
                PCA_METHOD="covariance PCA on shared valid pixels; centered, not standardized",
                INPUT_STACK=stack_path.name,
                VALID_PIXEL_COUNT=str(count),
                SIGN_CONVENTION="largest-magnitude loading is positive for reproducible output",
            )
            for component, value in enumerate(eigenvalues, 1):
                fraction = 100.0 * float(value) / total_variance if total_variance > 0 else 0.0
                output.update_tags(component, eigenvalue=f"{value:.12g}", variance_percent=f"{fraction:.8f}")

            for _, window in stack.block_windows(1):
                data, valid = read_valid_samples(stack, window)
                scores = np.full((6, *valid.shape), NODATA, dtype=np.float32)
                if np.any(valid):
                    centered = data[:, valid] - mean[:, None]
                    scores[:, valid] = (eigenvectors.T @ centered).astype(np.float32)
                output.write(scores, window=window)
    return count, eigenvalues


def paired_area_folders(pre_parent: Path, post_parent: Path) -> tuple[list[tuple[str, Path, Path]], list[str]]:
    pre_folders = {p.name.casefold(): p for p in pre_parent.iterdir() if p.is_dir()}
    post_folders = {p.name.casefold(): p for p in post_parent.iterdir() if p.is_dir()}
    matches = sorted(pre_folders.keys() & post_folders.keys())
    unmatched = sorted(
        [f"Pre only: {p.name}" for key, p in pre_folders.items() if key not in post_folders]
        + [f"Post only: {p.name}" for key, p in post_folders.items() if key not in pre_folders],
        key=str.casefold,
    )
    return [(pre_folders[key].name, pre_folders[key], post_folders[key]) for key in matches], unmatched


class PrePostPcaApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Pre/Post Image Stack + PCA")
        self.root.geometry("850x650")
        self.root.minsize(720, 560)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.pre_var = __import__("tkinter").StringVar()
        self.post_var = __import__("tkinter").StringVar()
        self.output_var = __import__("tkinter").StringVar()
        self.band_order_confirmed = __import__("tkinter").BooleanVar(value=False)

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        outer = ttk.Frame(root, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Pre/Post Image Stack + PCA", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Pair matching area folders, validate their raster grids, create a six-band stack, then calculate PC1–PC6.",
            wraplength=790,
        ).pack(anchor="w", pady=(3, 14))

        self.path_row(outer, "Pre-image parent folder", self.pre_var, self.choose_pre)
        self.path_row(outer, "Post-image parent folder", self.post_var, self.choose_post)
        self.path_row(outer, "Save results in", self.output_var, self.choose_output)

        note = (
            "Each parent folder should contain one subfolder per area. The matching area folders must each contain exactly "
            "one 3-band raster. Bands are read in B2, B3, B4 order. Results go to output\\area-name\\pre_post_stack.tif "
            "and output\\area-name\\pca_output.tif. The program checks CRS, extent, resolution, size and pixel grid. "
            "Grid metadata cannot prove real-world image co-registration; use imagery already accurately co-registered."
        )
        ttk.Label(outer, text=note, wraplength=790, justify="left", foreground="#444444").pack(anchor="w", pady=(0, 12))
        ttk.Checkbutton(
            outer,
            text="I confirm unnamed input bands are ordered B2, B3, B4 in both images.",
            variable=self.band_order_confirmed,
        ).pack(anchor="w", pady=(0, 10))

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x")
        self.status = __import__("tkinter").StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(5, 5))
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True)
        self.log = __import__("tkinter").Text(log_frame, height=12, wrap="word", font=("Consolas", 9), state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.run_button = ttk.Button(outer, text="Create stacks and run PCA", command=self.start_processing)
        self.run_button.pack(anchor="e", pady=(12, 0))
        self.root.after(100, self.check_events)

    def path_row(self, parent, label, variable, command) -> None:
        ttk.Label(parent, text=label, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(3, 10))
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=command).pack(side="left", padx=(8, 0))

    def choose_pre(self) -> None:
        value = filedialog.askdirectory(title="Choose parent folder containing pre-image area folders", mustexist=True)
        if value:
            self.pre_var.set(value)

    def choose_post(self) -> None:
        value = filedialog.askdirectory(title="Choose parent folder containing post-image area folders", mustexist=True)
        if value:
            self.post_var.set(value)

    def choose_output(self) -> None:
        value = filedialog.askdirectory(title="Choose output folder", mustexist=True)
        if value:
            self.output_var.set(value)

    def start_processing(self) -> None:
        if not self.band_order_confirmed.get():
            messagebox.showinfo("Confirm band order", "Confirm that unnamed input rasters use B2, B3, B4 band order before running.")
            return
        paths = [Path(var.get()).expanduser() for var in (self.pre_var, self.post_var, self.output_var)]
        if any(not path.is_dir() for path in paths):
            messagebox.showinfo("Choose folders", "Choose existing pre-image, post-image, and output folders.")
            return
        pre_parent, post_parent, output_parent = (p.resolve() for p in paths)
        if output_parent == pre_parent or output_parent == post_parent:
            messagebox.showinfo("Choose a separate output folder", "The output folder must be separate from both input parent folders.")
            return
        self.run_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set("Processing matching areas…")
        self.log.configure(state="normal")
        self.log.delete("1.0", END)
        self.log.configure(state="disabled")
        threading.Thread(target=self.process, args=(pre_parent, post_parent, output_parent), daemon=True).start()

    def process(self, pre_parent: Path, post_parent: Path, output_parent: Path) -> None:
        try:
            matches, unmatched = paired_area_folders(pre_parent, post_parent)
            if unmatched:
                self.events.put(("log", "Skipped unmatched folders: " + "; ".join(unmatched)))
            if not matches:
                raise ProcessingError("No matching area folder names were found in the pre and post parents.")
            successes = 0
            failures: list[str] = []
            for index, (area, pre_folder, post_folder) in enumerate(matches, 1):
                self.events.put(("status", f"Area {index}/{len(matches)}: {area}"))
                out_area = output_parent / area
                out_area.mkdir(parents=True, exist_ok=True)
                try:
                    pre_path = find_area_raster(pre_folder)
                    post_path = find_area_raster(post_folder)
                    stack_path = out_area / "pre_post_stack.tif"
                    pca_path = out_area / "pca_output.tif"
                    self.events.put(("log", f"{area}: validating and stacking\n  Pre: {pre_path}\n  Post: {post_path}"))
                    valid_count = stack_area(pre_path, post_path, stack_path)
                    pca_count, eigenvalues = create_pca(stack_path, pca_path)
                    successes += 1
                    variance = eigenvalues / eigenvalues.sum() * 100 if eigenvalues.sum() else np.zeros(6)
                    self.events.put(("log", f"{area}: complete ({valid_count:,} shared valid pixels)\n  {stack_path}\n  {pca_path}\n  PC4 variance: {variance[3]:.3f}%"))
                except Exception as exc:
                    failures.append(f"{area}: {exc}")
                    self.events.put(("log", f"{area}: skipped — {exc}"))
            self.events.put(("done", (successes, failures, len(matches), output_parent)))
        except Exception as exc:
            self.events.put(("fatal", str(exc)))

    def check_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert(END, str(payload) + "\n\n")
                    self.log.see(END)
                    self.log.configure(state="disabled")
                elif kind == "status":
                    self.status.set(str(payload))
                elif kind == "fatal":
                    self.finish()
                    self.status.set("Stopped")
                    messagebox.showerror("Could not process images", str(payload))
                elif kind == "done":
                    successes, failures, total, output = payload  # type: ignore[misc]
                    self.finish()
                    self.status.set(f"Finished: {successes}/{total} area(s) processed")
                    if failures:
                        messagebox.showwarning(
                            "Finished with skipped areas",
                            f"Processed {successes} of {total} matching areas.\n\n" + "\n".join(failures) + f"\n\nOutput: {output}",
                        )
                    else:
                        messagebox.showinfo("PCA complete", f"Processed {successes} area(s).\n\nOutput: {output}")
        except queue.Empty:
            pass
        self.root.after(100, self.check_events)

    def finish(self) -> None:
        self.progress.stop()
        self.run_button.configure(state="normal")


def main() -> None:
    root = Tk()
    PrePostPcaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

