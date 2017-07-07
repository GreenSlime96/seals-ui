import logging
import numpy
import cv2
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

import camera
import rect

frame_timeout = 200

class Focus(Gtk.Window):
    def destroy_cb(self, widget, data=None):
        if self.preview_timeout:
            GLib.source_remove(self.preview_timeout)

        self.destroy()

    def __init__(self, camera, selection):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)

        left = selection.left + int(selection.width / 2) - 400
        top = selection.top + int(selection.height / 2) - 300

        camera.focus_area(rect.Rect(left, top, 800, 600))

        self.image = Gtk.Image()
        self.add(self.image)
        self.image.show()

        self.image.set_app_paintable(True)

        self.frame_buffer = None
        self.preview_timeout = GLib.timeout_add(frame_timeout, self.live_cb)
        self.camera = camera
        self.frame = 0

    def live_cb(self):
        self.grab_frame()
        return True

    def grab_frame(self):
        logging.debug('grabbing frame ..')
        frame = self.camera.focus()

        if self.frame_buffer is frame:
            return

        # start_time = time.time()
        rgb_image = numpy.array(frame['data'], dtype="uint8").reshape((
            frame['rows'],
            frame['cols'],
            3))
        print("score %f" % cv2.Laplacian(rgb_image, cv2.CV_64F).var())
        # print("time taken: %f" % (time.time() - start_time))


        pixbuf = GdkPixbuf.Pixbuf.new_from_data(bytes(frame['data']),
                                                GdkPixbuf.Colorspace.RGB,
                                                False,
                                                8,
                                                frame['cols'],
                                                frame['rows'],
                                                frame['cols'] * 3,
                                                None, None)

        self.image.set_from_pixbuf(pixbuf)

        self.frame_buffer = frame
        self.frame += 1
