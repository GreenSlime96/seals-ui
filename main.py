#!/usr/bin/python

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

# how long to keep the play/pause button visible after a mouse event,
# in milliseconds
preview_timeout = 5000

#1060 x 706 pixels for preview

class MainWindow(Gtk.Window):

    def destroy_cb(self, widget, data=None):
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

        self.live_hide_timeot = GLib.timeout_add(preview_timeout,
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

    def __init__(self):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)

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

        self.play_image = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY,
                                                   Gtk.IconSize.SMALL_TOOLBAR)
        self.pause_image = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY,
                                                    Gtk.IconSize.SMALL_TOOLBAR)
        self.live = Gtk.Button()
        self.live.set_image(self.play_image)
        self.live.set_tooltip_text("Start/stop live preview")
        self.live.connect('clicked', self.live_cb, None)
        eb.add(self.live)
        self.live.show()

        self.show()


    def main(self):
        Gtk.main()

def main():
    window = MainWindow()
    window.main()

# if we are run directly, show our window
if __name__ == '__main__':
    main()
