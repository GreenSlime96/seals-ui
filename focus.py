import logging
import numpy
import cv2
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

gi.require_version('Vips', '8.0')
from gi.repository import Vips

import camera
import rect

# milliseconds between frame refreshes, 50 gives 20fps
frame_timeout = 50

# laplacian filter for image scoring
mask = Vips.Image.new_from_array([[0, 1,  0],
                                  [1, -4,  1],
                                  [0, 1,  0]])

class Focus(Gtk.Window):
    def destroy_cb(self, widget, data=None):
        if self.preview_timeout:
            GLib.source_remove(self.preview_timeout)

        if self.fps_timeout:
            GLib.source_remove(self.fps_timeout)

        print("min: %f" % min(self.times))
        print("max: %f" % max(self.times))
        print("avg: %f" % (sum(self.times)/len(self.times)))

        self.destroy()

    def __init__(self, camera, selection):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)

        left = selection.left + int(selection.width / 2) - 400
        top = selection.top + int(selection.height / 2) - 300

        self.times = []

        camera.focus_area(rect.Rect(0, 0, 800, 600))

        self.image = Gtk.Image()
        self.add(self.image)
        self.image.show()

        self.image.set_app_paintable(True)

        self.frame_buffer = None
        self.preview_timeout = GLib.timeout_add(frame_timeout, self.live_cb)
        self.fps_timeout = GLib.timeout_add(1000, self.fps_cb)
        self.camera = camera
        self.frame = 0

    def live_cb(self):
        self.grab_frame()
        return True

    def fps_cb(self):
        # print('fps = %d' % self.frame)
        self.frame = 0
        return True

    def grab_frame(self):
        logging.debug('grabbing frame ..')
        frame = self.camera.focus()

        if self.frame_buffer is frame:
            return

        start_time = time.time()

        score = cv2.Laplacian(cv2.cvtColor(frame['array'], cv2.COLOR_RGB2GRAY), cv2.CV_64F).var()
        # cv2.putText(frame['array'],
        #             "Score: {:.2f}".format(score),
        #             (10, 30),
        #             cv2.FONT_HERSHEY_SIMPLEX,
        #             0.8,
        #             (0, 0, 255),
        #             3)

        # memory = frame['array'].tobytes()
        # image2 = Vips.Image.new_from_memory(memory,
        #                                     frame['cols'],
        #                                     frame['rows'],
        #                                     3,
        #                                     Vips.BandFormat.UCHAR)
        #
        # image2 = image2.colourspace(Vips.Interpretation.B_W)
        # im = image2.conv(mask, precision=Vips.Precision.FLOAT)
        # score = im.deviate() ** 2
        # print("score: %f, %f" % (im.deviate()**2, score))

        self.times.append(time.time() - start_time)
        # print("score: %f" % score)

        # print("old: %d, new: %d" % (image2.bands, im.bands))

        # mem = im.write_to_memory()
        # print(len(mem) == len(memory))
        # x = im.write_to_memory()

        # pixbuf = GdkPixbuf.Pixbuf.new_from_data(x,
        #                                         GdkPixbuf.Colorspace.RGB,
        #                                         False,
        #                                         8,
        #                                         im.width,
        #                                         im.height,
        #                                         im.width * 3,
        #                                         None, None)

        # pixbuf = GdkPixbuf.Pixbuf.new_from_data(frame['array'].tobytes(),
        #                                         GdkPixbuf.Colorspace.RGB,
        #                                         False,
        #                                         8,
        #                                         frame['cols'],
        #                                         frame['rows'],
        #                                         frame['cols'] * 3,
        #                                         None, None)
        #
        # self.image.set_from_pixbuf(pixbuf)

        self.frame_buffer = frame
        self.frame += 1
