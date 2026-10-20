"""Interface themes (UserSettings.theme).

Each theme is drawn on top of Bootstrap's light or dark mode (`base`); "auto" follows
the operating system. The colours are --fi-* tokens: static/css/themes/default.css
holds the full list with the light and dark values, and a theme only overrides the
tokens it changes in static/css/themes/<key>.css, under [data-theme-pref="<key>"].

A theme can also go further than colours: give it "styled": True and its stylesheet
can set the shape and text tokens used by static/css/themes/styled.css (surfaces,
text colour, card radius and shadow, heading font...), see that file.

A theme can also add decorations: give it "script": True and create
static/js/themes/<key>.js. Every theme script is loaded on every page and must do
nothing unless <html data-theme-pref> is its key (the theme can be switched live).

To add a theme: add an entry here and create its stylesheet (and its script).
Nothing else to change: the settings page, the validation and base.html read this dict.
"""

# In the order shown on the settings page.
# key -> Bootstrap mode it is based on ("auto" = the OS one), label and Font Awesome
#        icon on the settings page, whether it has its own stylesheet, whether it uses
#        the styled layer (styled.css), whether it has a decorations script
THEMES = {
    "auto": {"base": "auto", "label": "System", "icon": "fa-circle-half-stroke"},
    "light": {"base": "light", "label": "Light", "icon": "fa-sun"},
    "dark": {"base": "dark", "label": "Dark", "icon": "fa-moon"},
    "neon": {"base": "dark", "label": "Neon", "icon": "fa-gamepad", "stylesheet": True, "styled": True},
    "arena": {"base": "light", "label": "Arena", "icon": "fa-trophy", "stylesheet": True, "styled": True},
    "linen": {"base": "light", "label": "Linen", "icon": "fa-scroll", "stylesheet": True, "styled": True},
    "tour": {"base": "light", "label": "Yellow Jersey", "icon": "fa-person-biking", "stylesheet": True, "styled": True, "script": True},
    "christmas": {"base": "dark", "label": "Christmas", "icon": "fa-tree", "stylesheet": True, "script": True},
}

DEFAULT_THEME = "auto"


def theme_styled(theme):
    return bool(THEMES.get(theme, {}).get("styled"))


def theme_base(theme):
    """Bootstrap mode of a theme as rendered by the server ("auto" is resolved in the browser)."""
    base = THEMES.get(theme, THEMES[DEFAULT_THEME])["base"]
    return "dark" if base == "dark" else "light"
