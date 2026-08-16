from librehub import theme, tray


class FakeIconTheme:
    def __init__(self, *names):
        self._names = set(names)

    def has_icon(self, name):
        return name in self._names


def test_uses_our_icon_when_it_is_installed():
    assert tray.icon_name(FakeIconTheme(theme.ICON_NAME)) == theme.ICON_NAME


def test_falls_back_to_the_stock_icon_when_ours_is_missing():
    assert tray.icon_name(FakeIconTheme("input-mouse")) == "input-mouse"


def test_falls_back_when_the_theme_has_neither():
    assert tray.icon_name(FakeIconTheme()) == tray.FALLBACK_ICON_NAME
