import os
import logging
import time
import sys
import shutil

import argparse

# from thorpy.comm.discovery import discover_stages
# from thorpy.message import *

import preview
import camera
import progress
import info
import focus
import rect
# import config

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

# 1060 x 706 pixels for preview
preview_width = 1060

class MainWindow(Gtk.Window):

    def destroy_cb(self, widget, data=None):
        if self.focus_window:
            self.focus_window.destroy()
            self.focus_window = None
            print("destroyed focus window")

        self.camera.release()
        print("destroyed camera")

        Gtk.main_quit()
        print("quit UI")

    def capture_cb(self, widget, data=None):
        pass
        # acceleration = self.stage.acceleration
        # velocity = 2
        #
        # self.stage.min_velocity = velocity
        # self.stage.max_velocity = velocity
        #
        # time.sleep(1)
        #
        #
        # self.stage.position = self.stage.position + 360
        #
        # print("acceleration: %f" % self.stage.acceleration)
        #
        # for i in range(10):
        #     print("current position: %f" % self.stage.position)
        #     time.sleep(1)

    def focus_destroy_cb(self, widget, data=None):
        self.preview.set_live(True)
        self.focus_window = None

    def focus_cb(self, widget, data=None):
        self.preview.set_live(False)

        if self.focus_window:
            self.focus_window.present()
        else:
            sel = self.preview.get_selection() or rect.Rect(0, 0, 1060 * 4, 706 * 4)

            self.focus_window = focus.Focus(self.camera, sel)
            self.focus_window.connect('destroy', self.focus_destroy_cb)
            self.focus_window.set_modal(True)
            self.focus_window.show()


    def __init__(self):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_resizable(False)

        # self.stage = next(discover_stages(), None)
        #
        # if self.stage is None:
        #     logging.error("Unable to find THORLABS stage")
        #     raise SystemExit(0)

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

        label = Gtk.Label()


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

        button = Gtk.Button('Capture')
        button.set_tooltip_text("Focus camera automatically")
        button.connect('clicked', self.capture_cb, None)
        self.toolbar.pack_start(button, False, False, 0)
        button.show()

        self.info.msg('Sharing Life\'s Happiness', 'v0.1, July 2017')
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
