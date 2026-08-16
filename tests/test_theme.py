from librehub import theme


def test_white_is_light():
    assert theme.is_light_color(1.0, 1.0, 1.0)


def test_black_is_not_light():
    assert not theme.is_light_color(0.0, 0.0, 0.0)


def test_adwaita_dark_background_is_not_light():
    assert not theme.is_light_color(45 / 255, 45 / 255, 45 / 255)


def test_space_dark_background_is_not_light():
    assert not theme.is_light_color(28 / 255, 31 / 255, 37 / 255)


def test_breeze_background_is_not_light_despite_its_name():
    assert not theme.is_light_color(49 / 255, 49 / 255, 58 / 255)


def test_green_is_weighted_by_luminance_not_average():
    assert theme.is_light_color(0.0, 1.0, 0.0)


def test_pure_blue_is_dark():
    assert not theme.is_light_color(0.0, 0.0, 1.0)
