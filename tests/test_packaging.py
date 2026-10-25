import sys
from types import SimpleNamespace

import aqt
from aqt import gui_hooks
from aqt.addons import AddonManager, InstallOk
from aqt.qt import QAction, QMenu

from tools.build import build


def test_package_installs_and_registers_tools_menu(window, tmp_path, monkeypatch):
    # Anki's own installer and loader, isolated from the user's profile.
    mw = window.mw
    addons_folder = tmp_path / "addons21"
    addons_folder.mkdir()
    mw.pm = SimpleNamespace(addonFolder=lambda: str(addons_folder))
    mw.form = SimpleNamespace(actionAdd_ons=QAction(mw), menuTools=QMenu(mw))
    monkeypatch.setattr(aqt, "mw", mw)
    hook_count = len(gui_hooks.profile_will_close._hooks)
    manager = AddonManager(mw)
    try:
        installed = manager.install(str(build()))
        assert isinstance(installed, InstallOk) and installed.compatible
        manager.loadAddons()
        assert [a.text() for a in mw.form.menuTools.actions()] == ["Anki Star…"]
        mw.form.menuTools.actions()[0].trigger()
        assert mw._anki_star_dialog.windowTitle().startswith("Anki Star")
        mw._anki_star_dialog.close()
    finally:
        del gui_hooks.profile_will_close._hooks[hook_count:]
        sys.path.remove(str(addons_folder))
        for module in list(sys.modules):
            if module == "anki_star" or module.startswith("anki_star."):
                sys.modules.pop(module)
