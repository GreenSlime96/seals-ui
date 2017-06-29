import logging

import PyCapture2

# track the detailed part of the last error generated by a subsystem here
# we present it with a summary during error messages
last_detail = ""


class Error(Exception):
    """An error from the camera.
    message -- a high-level description of the error
    detail -- a string with some detailed diagnostics
    """

    def __init__(self, message, detail=None):
        global last_detail

        self.message = message
        if detail:
            self.detail = detail
        else:
            self.detail = last_detail

        logging.debug('camera: Error %s %s', self.message, self.detail)

    def __str__(self):
        return '%s - %s' % (self.message, self.detail)


class Camera:
    """Talk to a USB camera with PyCapture2."""

    def __init__(self):
        """Initialise the PyCapture2 Camera."""
        self.busManager = PyCapture2.BusManager()
        self.camera = PyCapture2.Camera()

    def connect(self):
        """Connect to the camera.

        If currently unattached, automatically connect to any attached
        camera. This method is called for you before any camera operation.
        """
        if not self.camera.isConnected:
            logging.debug('** camera init')
            numCams = self.busManager.getNumOfCameras()

            if not numCams:
                self.release()
                raise Error('No cameras detected')

            try:
                uid = self.busManager.getCameraFromIndex(0)
                self.camera.connect(uid)
            except PyCapture2.Fc2error:
                raise Error('Unable to connect to camera')

            logging.debug('** camera connected')
        else:
            # Stop any captures if existing
            try:
                self.camera.stopCapture()
            except PyCapture2.Fc2error:
                pass

    def release(self):
        """Drop the camera connection.

        Calling this method will force reconnection on the next camera
        operation.
        """
        if self.camera.isConnected:
            logging.debug('** camera shutdown')

            try:
                self.camera.stopCapture()
            except PyCapture2.Fc2error:
                pass

            self.camera.disconnect()

    def preview(self):
        """Connect and capture a preview frame.

        Return the preview as a(data, length) tuple pointing to a memory
        area containing a jpeg-compressed image. The data poiner is only valid
        until the next call to preview().
        Preview can fail for short periods. If you get None back, try again
        later.
        """
        logging.debug('** camera preview')

        self.connect()

        fmt7info, supported = self.camera.getFormat7Info(PyCapture2.
                                                         MODE.MODE_5)

        if not supported:
            raise Error("Format7 MODE_5 not supported")

        if PyCapture2.PIXEL_FORMAT.RGB & fmt7info.pixelFormatBitField == 0:
            raise Error("Pixel format is not supported")

        fmt7imgSet = PyCapture2.Format7ImageSettings(0, 0, 0,
                                                     fmt7info.maxWidth,
                                                     fmt7info.maxHeight,
                                                     PyCapture2.
                                                     PIXEL_FORMAT.RGB)

        fmt7pktInf, isValid = self.camera.validateFormat7Settings(fmt7imgSet)

        if not isValid:
            raise Error("Format7 settings are not valid")

        self.camera.setFormat7ConfigurationPacket(fmt7pktInf.
                                                  recommendedBytesPerPacket,
                                                  fmt7imgSet)

        self.camera.startCapture()
        retval = self.camera.retrieveBuffer()
        self.camera.stopCapture()

        logging.debug('preview: frame at addr %d, length %d', id(retval),
                      retval.getDataSize())

        return retval