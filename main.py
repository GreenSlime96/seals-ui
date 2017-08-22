import os
import logging
import time
import sys
import shutil

import argparse

from thorpy.comm.discovery import discover_stages
from thorpy.message import *

import preview
import camera
import progress
import info
import focus
import rect
import config

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

        if self.config_window:
            self.config_window.destroy()
            self.config_window = None

        print("destroying")

        self.camera.release()

        Gtk.main_quit()

    def config_destroy_cb(self, widget, data=None):
        pass


    def config_cb(self, widget, data=None):
        if self.config_window:
            self.config_window.present()
        else:
            self.config_window = config.Config(self.camera)
            self.config_window.show()

    def capture_task(self, image):
        start = time.time()
        position = self.stage.position
        end = time.time()

        print(end - start)
        # time = timestamp.seconds + timestamp.microSeconds * 1e-06

        if self.busy:
            old_time = self.busy[1]
            new_time = time.time()

            delta_t = new_time - old_time

            old_pos = self.busy[0]
            new_pos = position

            delta_p = new_pos - old_pos

            # print(delta_p / delta_t, new_pos, new_time)

        self.busy = (position, time.time())

        if not self.capture_position:
            self.capture_stop()
        elif self.capture_position <= self.stage.position:
            self.capture_stop()

    def capture_start(self):
        max_velocity = self.max_velocity.get_value()

        self.stage.min_velocity = max_velocity
        self.stage.max_velocity = max_velocity

        # move turntable by 390 degrees (30 offset for start)
        self.capture_position = self.stage.position + 390

        self.stage.position = self.capture_position + 1
        self.camera.callback = self.capture_task

        pass

    def capture_stop(self):
        # stop the stage from moving
        self.stage.position = self.stage.position
        self.capture_position = None

        self.busy = None

        # stop camera callback from triggering processing
        self.camera.callback = None
        pass

    def capture_cb(self, widget, data=None):
        selection = self.preview.get_selection()

        if not selection:
            self.info.msg('ROI not Selected',
                          'Please draw a box around the seal.')
            
        elif self.capture_position:
            self.capture_stop()
        else:
            self.capture_start()


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


    def __init__(self, working_dir):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_resizable(False)
        self.set_title(working_dir)

        self.stage = next(discover_stages(), None)

        if self.stage is None:
            sys.exit("unable to locate THORLABS stage")

        self.working_dir = working_dir
        self.focus_window = None
        self.config_window = None
        self.capture_timeout = None
        self.busy = False

        self.capture_image = None
        self.capture_selection = None
        self.capture_position = None

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
        self.toolbar.pack_end(label, False, False, 0)
        self.preview.score_label = label
        label.show()

        button = Gtk.Button()
        menu_image = Gtk.Image.new_from_stock(Gtk.STOCK_PREFERENCES,
                                              Gtk.IconSize.SMALL_TOOLBAR)
        menu_image.show()
        button.set_tooltip_text("Camera settings")
        button.connect('clicked', self.config_cb, None)
        button.add(menu_image)
        self.toolbar.pack_start(button, False, False, 0)
        button.show()

        # button = Gtk.Button('Focus')
        # button.set_tooltip_text("Focus camera automatically")
        # button.connect('clicked', self.focus_cb, None)
        # self.toolbar.pack_start(button, False, False, 0)
        # button.show()

        spinner = Gtk.SpinButton.new_with_range(1, 4, 0.1)
        spinner.set_tooltip_text("Maximum velocity of turntable")
        spinner.set_value(self.stage.max_velocity)
        self.toolbar.pack_start(spinner, False, False, 0)
        self.max_velocity = spinner
        spinner.show()

        button = Gtk.Button('Capture')
        button.set_tooltip_text("Focus camera automatically")
        button.connect('clicked', self.capture_cb, None)
        self.toolbar.pack_start(button, False, False, 0)
        self.capture = button
        button.show()

        self.info.msg('Something Something Something', 'v0.1, July 2017')
        self.progress.progress(0.2)

        self.preview.set_live(True)

        self.show()



    def main(self):
        Gtk.main()

def main():
    # Prompt user for Working Directory
    chooser = Gtk.FileChooserDialog(title="Imaging Folder Selection",
                                    action=Gtk.FileChooserAction.SELECT_FOLDER,
                                    buttons=(Gtk.STOCK_OPEN,
                                             Gtk.ResponseType.OK))

    response = chooser.run()

    if response == Gtk.ResponseType.OK:
        filename = chooser.get_filename()
        chooser.destroy()

        window = MainWindow(filename)
        window.main()
    else:
        sys.exit("no folder chosen")




# if we are run directly, show our window
if __name__ == '__main__':
    main()
