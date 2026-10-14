def test_package_is_importable():
    import muthur

    assert muthur.__name__ == "muthur"
