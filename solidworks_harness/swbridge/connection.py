"""Attaching to a running SolidWorks session over COM.

Windows only. SolidWorks has no headless mode and no Linux build: the
application must actually be running, with a licence, on the machine
this code runs on.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from . import enums as E


class SolidWorksUnavailable(RuntimeError):
    """Raised when there is no SolidWorks to talk to."""


@dataclass
class Session:
    """A live SolidWorks application plus the document being built."""
    app: object                 # ISldWorks
    model: object | None = None  # IModelDoc2

    # ---- lifecycle --------------------------------------------------
    @classmethod
    def attach(cls, visible: bool = True) -> "Session":
        """Attach to a running SolidWorks, or start one."""
        if not sys.platform.startswith("win"):
            raise SolidWorksUnavailable(
                "SolidWorks is Windows-only COM software. This harness has "
                "to run on the same Windows machine as the SolidWorks "
                "installation; there is no remote or headless mode."
            )
        try:
            import win32com.client  # type: ignore
            import pythoncom  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise SolidWorksUnavailable(
                "pywin32 is required: pip install pywin32"
            ) from exc

        pythoncom.CoInitialize()
        try:
            # GetActiveObject reuses an open session, which matters: a
            # cold start costs 30-60 s and the agent loop may reconnect.
            app = win32com.client.GetActiveObject("SldWorks.Application")
        except Exception:
            app = win32com.client.Dispatch("SldWorks.Application")
        app.Visible = visible
        # Suppress modal dialogs -- a dialog waiting for a human click
        # will hang the agent loop with no error and no timeout.
        app.CommandInProgress = True
        return cls(app=app)

    # ---- documents --------------------------------------------------
    def new_part(self) -> object:
        template = self.app.GetUserPreferenceStringValue(E.PREF_TEMPLATE_PART)
        self.model = self.app.NewDocument(template, 0, 0.0, 0.0)
        self.model = self.app.ActiveDoc
        return self.model

    def new_assembly(self) -> object:
        template = self.app.GetUserPreferenceStringValue(
            E.PREF_TEMPLATE_ASSEMBLY
        )
        self.model = self.app.NewDocument(template, 0, 0.0, 0.0)
        self.model = self.app.ActiveDoc
        return self.model

    def open(self, path: str | Path) -> object:
        path = str(Path(path))
        errs, warns = 0, 0
        doc_type = E.DOC_ASSEMBLY if path.lower().endswith(".sldasm") else E.DOC_PART
        self.model = self.app.OpenDoc6(path, doc_type, 0, "", errs, warns)
        return self.model

    def save_as(self, path: str | Path) -> bool:
        """Save the active document. Returns True when SolidWorks agrees."""
        path = str(Path(path))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # SaveAs3 returns 0 on success; nonzero is a swFileSaveError_e.
        err = self.model.SaveAs3(path, 0, E.SAVE_SILENT)
        return err == 0 or err is True

    def close_all(self) -> None:
        self.app.CloseAllDocuments(True)

    def require_model(self) -> object:
        if self.model is None:
            raise RuntimeError("no active document; call new_part() first")
        return self.model
