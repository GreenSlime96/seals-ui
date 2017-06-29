import PyCapture2

import logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

import cv2
import numpy

import threading
import time

# Ensure sufficient cameras are found
bus = PyCapture2.BusManager()

# Select camera on 0th index
c = PyCapture2.Camera()
uid = bus.getCameraFromIndex(0)
# uid = bus.getCameraFromSerialNumber(17023355)
c.connect(uid)

# Configure camera format7 settings
fmt7info, supported = c.getFormat7Info(0)
# fmt7imgSet = PyCapture2.Format7ImageSettings(0, 0, 0, fmt7info.maxWidth, fmt7info.maxHeight, PyCapture2.PIXEL_FORMAT.RGB)
fmt7imgSet = PyCapture2.Format7ImageSettings(PyCapture2.MODE.MODE_0, 0, 0, fmt7info.maxWidth, fmt7info.maxHeight, PyCapture2.PIXEL_FORMAT.RGB)
fmt7pktInf, isValid = c.validateFormat7Settings(fmt7imgSet)
if not isValid:
    print("Format7 settings are not valid!")
    exit()

c.setFormat7ConfigurationPacket(fmt7pktInf.recommendedBytesPerPacket, fmt7imgSet)

# Capture a frame for testing
c.startCapture()

# GUI initialisation
window = Gtk.Window()
window.set_title("RIP")
window.connect("destroy", Gtk.main_quit)

image = Gtk.Image()

process = True
def live_view():
    while process:
        start_time= time.time()

        buff = c.retrieveBuffer()

        #https://stackoverflow.com/questions/44012780/get-image-from-point-grey-camera-using-pycapture2-and-opencv
        #https://stackoverflow.com/questions/7906814/converting-pil-image-to-gtk-pixbuf
        #https://stackoverflow.com/questions/30624988/memory-leak-when-showing-opencv-image-in-gtk-widget

        data = buff.getData()


        # cv_image = numpy.array(data, dtype="uint8").reshape((buff.getRows(), buff.getCols()))
        # cv_image = numpy.empty((buff.getRows(), buff.getCols()), dtype="uint8")

        # for x in range(buff.getCols()):
        #     for y in range(buff.getRows()):
        #         cv_image[y][x] = data[y * buff.getStride() + x]


        # x = y = 0
        # stride = buff.getStride()
        # for i in data:
        #     i = 0
        #     cv_image[y][x] = i
        #
        #     x += 1
        #
        #     if x == stride:
        #         x = 0
        #         y += 1



        # rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BAYER_BG2BGR)
        # rgb_image = numpy.array(data, dtype="uint8").reshape((buff.getRows(), buff.getCols(), 3))



        # Get details about frame in order to set up pixbuffer
        # height = rgb_image.shape[0]
        # width = rgb_image.shape[1]
        # nChannels = rgb_image.shape[2]
        height = buff.getRows()
        width = buff.getCols()
        nChannels = 3

        datum = bytes(data)
        # gbytes = GLib.Bytes.new(rgb_image.tostring())
        # gbytes = GLib.Bytes.new(b''.join(data))
        # gbytes = GLib.Bytes.new(bytes(data))

        gbytes = GLib.Bytes.new_take(datum)
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Pixbuf.Colorspace.RGB,
													False,
													8,
													frame.getCols(),
													frame.getRows(),
													width * nChannels)
													# None,
													# None)


        print("--- %s seconds ---" % (time.time() - start_time))

        GLib.idle_add(image.set_from_pixbuf, pixbuf.copy())
        GLib.idle_add(image.queue_draw)

        # gbytes.unref()


t = threading.Thread(target = live_view)
t.start()

window.add(image)
window.show_all()
Gtk.main()

process = False

# GdkPixbuf.Pixbuf.new_from_data(image.getData(), GdkPixbuf.Colorspace.RGB, False, 8, image.getCols(), image.getRows(), image.getStride())

c.stopCapture()
c.disconnect()
