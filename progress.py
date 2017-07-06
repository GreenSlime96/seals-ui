import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class Progress(Gtk.InfoBar):

    def cancel_cb(self ,widget, response_id, client):
        self.cancel = True

    def __init__(self):
        Gtk.InfoBar.__init__(self)

        self.cancel = False

        content = self.get_content_area()

        self.progressbar = Gtk.ProgressBar()
        content.pack_start(self.progressbar, True, True, 0)
        self.progressbar.show()

        self.add_button('Cancel', 0)
        self.connect('response', self.cancel_cb, None)

    def start(self, message):
        self.progressbar.set_text(message)
        self.progressbar.set_fraction(0)
        self.show()

    def progress(self, fraction):
        self.progressbar.set_fraction(fraction)

        while Gtk.events_pending():
            Gtk.main_iteration()

        return self.cancel

    def stop(self):
        self.hide()
        self.cancel = False
