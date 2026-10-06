"""Finder layout for the PDF2Word drag-and-drop macOS disk image."""

from __future__ import annotations

import os

application = defines["app"]  # noqa: F821
app_name = os.path.basename(application)
background = defines["background"]  # noqa: F821

files = [application]
symlinks = {"Applications": "/Applications"}
icon_locations = {
    app_name: (175, 225),
    "Applications": (525, 225),
}
format = "UDZO"
compression_level = 9
default_view = "icon-view"
window_rect = ((100, 100), (700, 450))
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
show_icon_preview = True
include_icon_view_settings = True
arrange_by = None
icon_size = 96
text_size = 14
