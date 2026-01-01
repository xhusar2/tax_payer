from __future__ import annotations

from pathlib import Path
from typing import Literal

import requests

from config.settings import TAX_PORTAL_PASSWORD, TAX_PORTAL_USERNAME

DocumentType = Literal["DPH", "DHK"]


class TaxPortalSubmitter:
    """
    Very rough HTTP submitter.

    The official Daňový portál is not really designed as a public API, so in
    practice you might either:
    - upload manually, or
    - use data box API / custom integration.

    For now this is just a stub you can fill in once you decide how you want to
    automate the submission.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.username = username or TAX_PORTAL_USERNAME
        self.password = password or TAX_PORTAL_PASSWORD
        self.session = requests.Session()

    def login(self) -> bool:
        """
        Stub for login process.
        If you later reverse‑engineer the login form, plug it in here.
        """
        if not (self.username and self.password):
            raise RuntimeError("Tax portal credentials not configured")
        # TODO: implement if you decide to automate browser‑less login
        return False

    def submit_xml(self, path: str | Path, doc_type: DocumentType) -> bool:
        """
        Stub for submitting XML.
        Right now just exists so the rest of the pipeline compiles.
        """
        _ = (path, doc_type)
        # TODO: implement once you know which channel you'll use (datovka / portal)
        raise NotImplementedError("Automatic submission not implemented yet")





