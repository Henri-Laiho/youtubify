from typing import Iterable

try:
    from simple_term_menu import TerminalMenu
    unix = True
except NotImplementedError:
    from consolemenu import SelectionMenu
    unix = False


class Menu:

    def __init__(self, menu_items: Iterable[str]):
        if unix:
            self.menu = TerminalMenu(menu_items)
        else:
            self.menu = SelectionMenu(menu_items, show_exit_option=False)


    def show(self):
        if unix:
            return self.menu.show()
        else:
            self.menu.show()
            self.menu.join()
            return self.menu.selected_option

