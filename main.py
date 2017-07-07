import os
import logging
import time
import sys
import shutil

import argparse

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

import preview
import camera
import progress
import info
import focus
# import config

# how long to keep the play/pause button visible after a mouse event,
# in milliseconds
preview_timeout = 5000

#1060 x 706 pixels for preview
preview_width = 1060

class MainWindow(Gtk.Window):

    def destroy_cb(self, widget, data=None):
        if self.focus_window:
            self.focus_window.destroy()
            self.focus_window = None

        self.camera.release()

        Gtk.main_quit()

    def preview_hide_cb(self):
        self.live_hide_timeout = 0
        self.live.hide()

        return False

    def preview_motion_cb(self, widget, event):
        self.live.show()

        if self.live_hide_timeout:
            GLib.source_remove(self.live_hide_timeout)
            self.live_hide_timeout = 0

        self.live_hide_timeout = GLib.timeout_add(preview_timeout,
                                                  self.preview_hide_cb)

        return True

    def set_live(self, live):
        if live:
            self.live.set_image(self.pause_image)
        else:
            self.live.set_image(self.play_image)

        self.preview.set_live(live)
        self.camera.release()

    def live_cb(self, widget, data=None):
        self.set_live(not self.preview.get_live())

    def focus_destroy_cb(self, widget, data=None):
        self.focus_window = None

    def focus_cb(self, widget, data=None):
        if self.focus_window:
            self.focus_window.present()
        else:
            self.focus_window = focus.Focus(self.camera,
                                            self.preview.get_selection())
            self.focus_window.connect('destroy', self.focus_destroy_cb)
            self.focus_window.show()


    def __init__(self):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)

        self.focus_window = None
        self.config_window = None
        self.live_hide_timeout = 0
        self.busy = False

        self.vbox = Gtk.VBox(False, 0)
        self.add(self.vbox)
        self.vbox.show()

        fixed = Gtk.Fixed()
        self.vbox.pack_start(fixed, False, True, 0)
        fixed.show()

        self.camera = camera.Camera()
        self.preview = preview.Preview(self.camera)
        fixed.put(self.preview, 0, 0)
        self.preview.show()
        self.preview.connect('motion_notify_event', self.preview_motion_cb)

        eb = Gtk.EventBox()
        fixed.put(eb, 0, 0)
        eb.show()

        self.progress = progress.Progress()
        self.progress.set_size_request(preview_width, -1)
        eb.add(self.progress)

        eb = Gtk.EventBox()
        fixed.put(eb, 0, 0)
        eb.show()

        self.info = info.Info()
        self.info.set_size_request(preview_width, -1)
        eb.add(self.info)

        eb = Gtk.EventBox()
        fixed.put(eb, 20, 380)
        eb.show()

        self.play_image = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY,
                                                   Gtk.IconSize.SMALL_TOOLBAR)
        self.pause_image = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PAUSE,
                                                    Gtk.IconSize.SMALL_TOOLBAR)
        self.live = Gtk.Button()
        self.live.set_image(self.play_image)
        self.live.set_tooltip_text("Start/stop live preview")
        self.live.connect('clicked', self.live_cb, None)
        eb.add(self.live)
        self.live.show()

        self.toolbar = Gtk.HBox(False, 5)
        self.toolbar.set_border_width(3)
        self.vbox.pack_end(self.toolbar, False, False, 0)
        self.toolbar.show()

        button = Gtk.Button()
        quit_image = Gtk.Image.new_from_stock(Gtk.STOCK_QUIT,
                                              Gtk.IconSize.SMALL_TOOLBAR)
        quit_image.show()
        button.set_tooltip_text("Quit RTIAcquire")
        button.connect('clicked', self.destroy_cb, None)
        button.add(quit_image)
        self.toolbar.pack_end(button, False, False, 0)
        button.show()

        button = Gtk.Button()
        menu_image = Gtk.Image.new_from_stock(Gtk.STOCK_PREFERENCES,
                                              Gtk.IconSize.SMALL_TOOLBAR)
        menu_image.show()
        button.set_tooltip_text("Camera settings")
        # button.connect('clicked', self.config_cb, None)
        button.add(menu_image)
        self.toolbar.pack_start(button, False, False, 0)
        button.show()

        button = Gtk.Button('Focus')
        button.set_tooltip_text("Focus camera automatically")
        button.connect('clicked', self.focus_cb, None)
        self.toolbar.pack_start(button, False, False, 0)
        button.show()

        self.info.msg('Welcome to Boon Nick Kirk Jon', 'v0.1, July 2017')
        self.progress.progress(0.2)

        self.show()


    def main(self):
        Gtk.main()

def main():
    window = MainWindow()
    window.main()

# if we are run directly, show our window
if __name__ == '__main__':
    main()
