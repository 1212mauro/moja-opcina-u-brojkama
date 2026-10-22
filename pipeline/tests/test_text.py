from opcina_pipeline.text import ascii_fold, name_key, slugify


def test_ascii_fold_removes_croatian_diacritics():
    assert ascii_fold("Čakovec") == "cakovec"
    assert ascii_fold("Đurđevac") == "durdevac"
    assert ascii_fold("ŽUPANIJA Šibensko") == "zupanija sibensko"


def test_slugify():
    assert slugify("Breznički Hum") == "breznicki-hum"
    assert slugify("Grad Varaždinske Toplice") == "grad-varazdinske-toplice"
    assert slugify("Donje Vratno (Petrijanec)") == "donje-vratno-petrijanec"


def test_name_key_ignores_case_spacing_and_diacritics():
    assert name_key("BREZNIČKI  HUM") == name_key("Breznički Hum")
