"""Anki loads this module; pure Python helpers also work outside Anki."""


def register():
    from aqt import gui_hooks, mw
    from aqt.qt import QAction

    def open_star():
        from .ui import StarDialog

        dialog = getattr(mw, "_anki_star_dialog", None)
        if dialog is None:
            dialog = StarDialog(mw)
            mw._anki_star_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def close_star():
        dialog = getattr(mw, "_anki_star_dialog", None)
        if dialog:
            dialog.close()
            dialog.deleteLater()
            mw._anki_star_dialog = None

    action = QAction("Anki Star…", mw)
    action.triggered.connect(open_star)
    mw.form.menuTools.addAction(action)
    gui_hooks.profile_will_close.append(close_star)


try:
    import aqt  # noqa: F401
except ImportError:
    pass
else:
    # Importing helpers in tests must not register against an unstarted Anki.
    if aqt.mw is not None:
        register()
