# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The window's language: the saved choice, the system's, the menu and the buttons."""

import sys

import pytest
from PySide6.QtCore import QLocale, QSettings
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

import optar_gui.__main__ as entry
import optar_gui.main_window as main_window
from optar import i18n
from optar_gui import dialogs, language, selftest, text

RU = {
    "language": {"name": "Русский"},
    "gui": {
        "READ_TAB": "Чтение",
        "LANGUAGE_MENU": "Язык",
        "SYSTEM_LANGUAGE": "Как в системе",
        "LANGUAGE_RESTART": "Язык сменится при следующем запуске.",
        "button": {"save": "Сохранить", "cancel": "Отмена", "ok": "ОК"},
        "cli": {"missing_qt": "Нужен PySide6.", "description": "d", "version_help": "v"},
    },
}


def write_raw(raw):
    settings = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "optar", "optar-gui"
    )
    settings.setValue("language", raw)
    settings.sync()


def test_nothing_saved_gives_the_system_language(catalogues, monkeypatch):
    catalogues.add("ru", RU)
    assert language.saved() is None
    assert language.at_start() == "en"
    monkeypatch.setattr(QLocale, "system", staticmethod(lambda: QLocale("ru_RU")))
    assert language.system() == "ru"
    assert language.at_start() == "ru"


def test_a_saved_choice_wins_over_the_system(catalogues, monkeypatch):
    catalogues.add("ru", RU)
    monkeypatch.setattr(QLocale, "system", staticmethod(lambda: QLocale("ru_RU")))
    language.save("en")
    assert language.at_start() == "en"


@pytest.mark.parametrize("raw", ["xx", "", 7, "RU "])
def test_bad_saved_choice_is_ignored(catalogues, raw):
    catalogues.add("ru", RU)
    write_raw(raw)
    assert language.saved() is None
    assert language.at_start() == "en"


def test_save_and_read_back(catalogues):
    catalogues.add("pl", {"language": {"name": "Polski"}})
    language.save("pl")
    assert language.saved() == "pl"
    language.save(None)
    assert language.saved() is None


def menu_actions(window):
    return window.language_menu.actions()


def test_menu_lists_every_language_by_its_own_name(qtbot, catalogues):
    catalogues.add("ru", RU)
    window = main_window.MainWindow()
    qtbot.addWidget(window)
    assert window.language_menu.title() == text.LANGUAGE_MENU
    actions = menu_actions(window)
    assert [a.text() for a in actions] == [text.SYSTEM_LANGUAGE, *i18n.languages().values()]
    assert [a.isChecked() for a in actions].count(True) == 1
    assert actions[0].isChecked()  # nothing saved: follow the system


def test_the_saved_language_is_the_checked_entry(qtbot, catalogues):
    catalogues.add("ru", RU)
    language.save("ru")
    window = main_window.MainWindow()
    qtbot.addWidget(window)
    checked = [a.data() for a in menu_actions(window) if a.isChecked()]
    assert checked == ["ru"]


def test_choosing_a_language_saves_it_and_says_restart(qtbot, catalogues, monkeypatch):
    catalogues.add("ru", RU)
    shown = []
    monkeypatch.setattr(
        main_window, "ask", lambda parent, icon, title, message, *a: shown.append(message)
    )
    window = main_window.MainWindow()
    qtbot.addWidget(window)
    tab_before = window.tabs.tabText(0)
    ru = next(a for a in menu_actions(window) if a.data() == "ru")
    ru.trigger()
    assert language.saved() == "ru"
    assert shown == [text.LANGUAGE_RESTART]
    assert window.tabs.tabText(0) == tab_before
    assert window.language_menu.title() == "Language"
    menu_actions(window)[0].trigger()  # back to the system's language
    assert language.saved() is None


def test_message_box_buttons_come_from_the_catalogue(qtbot, catalogues, monkeypatch):
    catalogues.add("ru", RU)
    i18n.set_language("ru")
    made = []
    real_exec = QMessageBox.exec

    def exec_(box):
        made.append({b.text() for b in box.buttons()})
        return real_exec  # not run: the box is not shown

    monkeypatch.setattr(QMessageBox, "exec", exec_)
    save, cancel = QMessageBox.StandardButton.Save, QMessageBox.StandardButton.Cancel
    dialogs.ask(None, QMessageBox.Icon.Question, "t", "m", save | cancel)
    assert made == [{"Сохранить", "Отмена"}]
    dialog = dialogs.AssignPageDialog(3)
    qtbot.addWidget(dialog)
    box = dialog.findChild(QDialogButtonBox)
    assert {b.text() for b in box.buttons()} == {"ОК", "Отмена"}


def test_missing_qt_message_follows_the_environment(catalogues, monkeypatch, capsys):
    catalogues.add("ru", RU)
    monkeypatch.setitem(sys.modules, "PySide6", None)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", None)
    monkeypatch.setenv("OPTAR_LANG", "ru")
    assert entry.main([]) == 2
    assert capsys.readouterr().err == "Нужен PySide6.\n"
    assert i18n.language() == "en"  # main puts the language back


def test_self_test_runs_in_english_and_loads_every_catalogue(qapp, catalogues, capsys):
    catalogues.add("ru", RU)
    i18n.set_language("ru")
    assert selftest.run_self_test() == 0
    out = capsys.readouterr().out
    assert "ok loaded the catalogues of 2 languages" in out
    assert "ok created a PDF" in out
    assert i18n.language() == "ru"
