from __future__ import annotations

"""Repository desktop tool for batch APICORE validation."""

import tkinter as tk
from pathlib import Path
from time import perf_counter
from tkinter import filedialog, messagebox, ttk
from typing import Any, ClassVar

from apicore import APICoreError, load


class _Result:
    __slots__ = ("detail", "doc", "elapsed_ms", "path", "status")

    def __init__(
        self,
        path: str,
        status: str,
        detail: str,
        doc: Any = None,
        elapsed_ms: float = 0.0,
    ) -> None:
        self.path = path
        self.status = status
        self.detail = detail
        self.doc = doc
        self.elapsed_ms = elapsed_ms


class APICoreValidatorGUI:
    """Tkinter application for validating and inspecting APICORE documents."""

    _SUPPORTED_EXTS: ClassVar[set[str]] = {".json", ".yaml", ".yml", ".toml"}
    _STATUS_COLORS: ClassVar[dict[str, str]] = {
        "OK": "#4caf50",
        "ERROR": "#f44336",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("APICORE Validator")
        self.root.geometry("1100x720")
        self.root.minsize(800, 500)

        self._results: list[_Result] = []
        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="Add Files", command=self._add_files).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(toolbar, text="Add Folder", command=self._add_folder).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(toolbar, text="Validate All", command=self._validate_all).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(toolbar, text="Clear", command=self._clear).pack(
            side=tk.LEFT, padx=(0, 4)
        )

        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(toolbar, textvariable=self._status_var).pack(side=tk.RIGHT, padx=4)

        pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        list_frame = ttk.Frame(pane)
        pane.add(list_frame, weight=2)

        columns = (
            "status",
            "version",
            "name",
            "method",
            "link",
            "params",
            "time_ms",
            "path",
        )
        self._tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse"
        )
        self._tree.heading("status", text="Status")
        self._tree.heading("version", text="Version")
        self._tree.heading("name", text="Friendly Name")
        self._tree.heading("method", text="Method")
        self._tree.heading("link", text="Link")
        self._tree.heading("params", text="Params")
        self._tree.heading("time_ms", text="Time(ms)")
        self._tree.heading("path", text="File Path")

        self._tree.column("status", width=60, minwidth=50, stretch=False)
        self._tree.column("version", width=60, minwidth=50, stretch=False)
        self._tree.column("name", width=140, minwidth=80)
        self._tree.column("method", width=60, minwidth=50, stretch=False)
        self._tree.column("link", width=240, minwidth=120)
        self._tree.column("params", width=50, minwidth=40, stretch=False)
        self._tree.column("time_ms", width=70, minwidth=55, stretch=False)
        self._tree.column("path", width=260, minwidth=120)

        scrollbar_y = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self._tree.yview
        )
        scrollbar_x = ttk.Scrollbar(
            list_frame, orient=tk.HORIZONTAL, command=self._tree.xview
        )
        self._tree.configure(
            yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set
        )
        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self._tree.tag_configure("ok", foreground="#2e7d32")
        self._tree.tag_configure("error", foreground="#c62828")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        detail_frame = ttk.LabelFrame(pane, text="Detail", padding=4)
        pane.add(detail_frame, weight=1)

        self._detail_text = tk.Text(
            detail_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10)
        )
        detail_scroll = ttk.Scrollbar(
            detail_frame, orient=tk.VERTICAL, command=self._detail_text.yview
        )
        self._detail_text.configure(yscrollcommand=detail_scroll.set)
        self._detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select APICORE Files",
            filetypes=[
                (
                    "APICORE files",
                    "*.api.json *.api.yaml *.api.yml *.api.toml *.json *.yaml *.yml *.toml",
                ),
                ("JSON", "*.json"),
                ("YAML", "*.yaml *.yml"),
                ("TOML", "*.toml"),
                ("All", "*.*"),
            ],
        )
        self._process_paths([Path(p) for p in paths])

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select Folder with APICORE Files")
        if not folder:
            return
        files: list[Path] = []
        for p in Path(folder).rglob("*"):
            if p.is_file() and p.suffix.lower() in self._SUPPORTED_EXTS:
                files.append(p)
        if not files:
            messagebox.showinfo("No Files", "No supported files found in the folder.")
            return
        self._process_paths(files)

    def _process_paths(self, paths: list[Path]) -> None:
        added = 0
        total_start = perf_counter()
        for path in paths:
            path_str = str(path)
            if any(r.path == path_str for r in self._results):
                continue
            result = self._parse_one(path)
            self._results.append(result)
            self._insert_row(result)
            added += 1
        total_ms = (perf_counter() - total_start) * 1000
        self._update_status(total_ms=total_ms)

    def _parse_one(self, path: Path) -> _Result:
        t0 = perf_counter()
        try:
            doc = load(path)
            elapsed = (perf_counter() - t0) * 1000
            return _Result(
                path=str(path),
                status="OK",
                detail="",
                doc=doc,
                elapsed_ms=elapsed,
            )
        except APICoreError as exc:
            elapsed = (perf_counter() - t0) * 1000
            return _Result(
                path=str(path),
                status="ERROR",
                detail=str(exc),
                doc=None,
                elapsed_ms=elapsed,
            )
        except (OSError, TypeError, ValueError) as exc:
            elapsed = (perf_counter() - t0) * 1000
            return _Result(
                path=str(path),
                status="ERROR",
                detail=f"Unexpected error: {exc}",
                doc=None,
                elapsed_ms=elapsed,
            )

    def _insert_row(self, result: _Result) -> None:
        doc = result.doc
        time_str = f"{result.elapsed_ms:.2f}"
        if doc is not None:
            values = (
                result.status,
                doc.apicore_version,
                doc.friendly_name,
                doc.func,
                doc.link,
                str(len(doc.parameters)),
                time_str,
                result.path,
            )
        else:
            values = (
                result.status,
                "-",
                "-",
                "-",
                "-",
                "-",
                time_str,
                result.path,
            )
        tag = "ok" if result.status == "OK" else "error"
        self._tree.insert("", tk.END, values=values, tags=(tag,))

    def _validate_all(self) -> None:
        old_paths = [Path(r.path) for r in self._results]
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._results.clear()

        total_start = perf_counter()
        for path in old_paths:
            result = self._parse_one(path)
            self._results.append(result)
            self._insert_row(result)
        total_ms = (perf_counter() - total_start) * 1000
        self._update_status(total_ms=total_ms)

    def _clear(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._results.clear()
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        self._detail_text.configure(state=tk.DISABLED)
        self._status_var.set("Ready")

    def _on_select(self, _event: tk.Event) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        item = selection[0]
        index = self._tree.index(item)
        if index >= len(self._results):
            return
        result = self._results[index]
        self._show_detail(result)

    def _show_detail(self, result: _Result) -> None:
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)

        lines: list[str] = []
        lines.append(f"File: {result.path}")
        lines.append(f"Status: {result.status}")
        lines.append(f"Parse Time: {result.elapsed_ms:.2f}ms")
        lines.append("")

        doc = result.doc
        if doc is not None:
            lines.append(f"Version:        {doc.apicore_version}")
            lines.append(f"Friendly Name:  {doc.friendly_name}")
            lines.append(f"Link:           {doc.link}")
            lines.append(f"Method:         {doc.func}")
            if doc.intro:
                lines.append(f"Intro:          {doc.intro}")
            if doc.icon:
                lines.append(f"Icon:           {doc.icon}")
            for label, value in (
                ("Schema", getattr(doc, "schema_url", None)),
                ("ID", getattr(doc, "id", None)),
                ("Config Version", getattr(doc, "version", None)),
                ("Author", getattr(doc, "author", None)),
                ("License", getattr(doc, "license", None)),
                ("Repository", getattr(doc, "repository", None)),
                ("Updated At", getattr(doc, "updated_at", None)),
            ):
                if value:
                    lines.append(f"{label + ':':<16}{value}")
            lines.append("")

            lines.append(f"Parameters ({len(doc.parameters)}):")
            for i, param in enumerate(doc.parameters):
                lines.append(f"  [{i}] {param.friendly_name}")
                lines.append(
                    f"      name={param.name}  type={param.type}  required={param.required}  enable={param.enable}"
                )
                value = "********" if param.text_secret else param.value
                lines.append(f"      value={value}")
                if param.friendly_value:
                    lines.append(f"      friendly_value={param.friendly_value}")
                if param.options:
                    lines.append(f"      options={param.options}")
                if param.friendly_options:
                    lines.append(f"      friendly_options={param.friendly_options}")
                if param.min_value is not None:
                    lines.append(f"      min_value={param.min_value}")
                if param.max_value is not None:
                    lines.append(f"      max_value={param.max_value}")
                if param.tooltip:
                    lines.append(f"      tooltip={param.tooltip}")
                if param.placeholder:
                    lines.append(f"      placeholder={param.placeholder}")
                if param.text_secret:
                    lines.append("      text_secret=True")
                if param.show_if:
                    lines.append(f"      show_if={param.show_if}")
                if param.extra:
                    lines.append(f"      extra={param.extra}")
            lines.append("")

            resp = doc.response
            lines.append("Response:")
            if resp.media is not None:
                lines.append("  Media (preferred):")
                lines.append(f"    type={resp.media.type}")
                lines.append(f"    content_type={resp.media.content_type}")
                lines.append(f"    path={resp.media.path}")
                lines.append(
                    f"    is_list={resp.media.is_list}  is_base64={resp.media.is_base64}"
                )
            if resp.image is not None:
                lines.append("  Image:")
                lines.append(f"    content_type={resp.image.content_type}")
                lines.append(f"    path={resp.image.path}")
                lines.append(
                    f"    is_list={resp.image.is_list}  is_base64={resp.image.is_base64}"
                )
            for i, group in enumerate(resp.others):
                lines.append(f"  Others[{i}]: {group.friendly_name}")
                for field in group.data:
                    lines.append(f"    {field.friendly_name} -> {field.path}")
            lines.append("")

            configs = getattr(doc, "configs", None)
            if configs is not None:
                lines.append("Configs:")
                if configs.request is not None:
                    lines.append(
                        f"  Request body_type={configs.request.body_type} "
                        f"timeout_ms={configs.request.timeout_ms}"
                    )
                    if configs.request.body_template is not None:
                        lines.append(
                            f"    body_template={configs.request.body_template}"
                        )
                    if configs.request.headers:
                        for k, v in configs.request.headers.items():
                            lines.append(f"    {k}: {v}")
                if configs.retry is not None:
                    lines.append(
                        f"  Retry count={configs.retry.count} delay_ms={configs.retry.delay_ms}"
                    )
                if configs.rate_limit is not None:
                    lines.append(
                        f"  RateLimit frequency={configs.rate_limit.frequency} per={configs.rate_limit.per}"
                    )
                if configs.polling is not None:
                    lines.append(
                        f"  Polling interval_ms={configs.polling.interval_ms} "
                        f"timeout_ms={configs.polling.timeout_ms}"
                    )
                    lines.append(f"    check_link={configs.polling.check_link}")
                    lines.append(f"    status_path={configs.polling.status_path}")
                    lines.append(f"    success_value={configs.polling.success_value}")
                    if configs.polling.failed_value is not None:
                        lines.append(f"    failed_value={configs.polling.failed_value}")
                lines.append("")

            handlers = getattr(doc, "handlers", None)
            if handlers:
                lines.append(f"Handlers ({len(handlers)}):")
                for key, handler in handlers.items():
                    lines.append(f"  [{key}] action={handler.action}")
                    if handler.message:
                        lines.append(f"      message={handler.message}")
                    if handler.link:
                        lines.append(f"      link={handler.link}")
                    if handler.script:
                        lines.append(f"      script={handler.script}")
                        lines.append(
                            "      SECURITY: High risk; require explicit user approval"
                        )
                    if handler.extract:
                        lines.append(f"      extract={handler.extract}")
                    if handler.count is not None:
                        lines.append(f"      count={handler.count}")
                    if handler.delay_ms is not None:
                        lines.append(f"      delay_ms={handler.delay_ms}")
        else:
            lines.append("Error:")
            lines.append(f"  {result.detail}")

        self._detail_text.insert("1.0", "\n".join(lines))
        self._detail_text.configure(state=tk.DISABLED)

    def _update_status(self, *, total_ms: float | None = None) -> None:
        total = len(self._results)
        ok = sum(1 for r in self._results if r.status == "OK")
        errors = total - ok
        parts = [f"Total: {total}", f"Valid: {ok}", f"Errors: {errors}"]
        if total_ms is not None:
            parts.append(f"Total time: {total_ms:.2f}ms")
        self._status_var.set("  |  ".join(parts))


def main() -> None:
    """Start the desktop validator event loop."""
    root = tk.Tk()
    APICoreValidatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
