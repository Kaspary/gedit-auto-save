import os
from datetime import datetime
import subprocess
from gi.repository import GObject, Gedit, Gio, Gtk

__all__ = ["SASViewActivatable", "SASWindowActivatable"]

TMP_FOLDER = '~/Documents/.gedit/'


class SASViewActivatable(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "SASViewActivatable"
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        """Initialize the view activatable."""
        GObject.Object.__init__(self)
        self.timeout_id = None

    def do_activate(self):
        """Activate the plugin and connect document changed signal."""
        self.document_changed_handler_id = self.document.connect("changed", self.document_changed)

    def do_deactivate(self):
        """Deactivate the plugin and disconnect document changed signal."""
        self.document.disconnect(self.document_changed_handler_id)

    def document_changed(self, _document):
        """Handle document change event and schedule saving."""
        if self.timeout_id is not None:
            GObject.source_remove(self.timeout_id)

        self.timeout_id = GObject.timeout_add(500, self.maybe_save, priority=GObject.PRIORITY_LOW)

    def maybe_save(self):
        """Save the document if conditions are met."""
        maybe_save(self.window)
        self.timeout_id = None

    @property
    def document(self):
        """Return the current document."""
        return self.view.get_buffer()

    @property
    def window(self):
        """Return the top-level window."""
        return self.view.get_toplevel()


class SASWindowActivatable(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "SASWindowActivatable"
    window = GObject.Property(type=Gedit.Window)

    def __init__(self):
        """Initialize the window activatable."""
        GObject.Object.__init__(self)
        self.is_closing = False

    def do_activate(self):
        """Activate the plugin and connect window signals."""
        self.window.smart_autosave_plugin_handler_ids = [
            self.window.connect("active-tab-changed", self.active_tab_changed),
            self.window.connect("focus-out-event", self.focus_out),
            self.window.connect("tab-removed", self.tab_removed),
            self.window.connect("delete-event", self.on_window_delete_event),
            self.window.connect("show", self.on_window_show)
        ]

    def do_deactivate(self):
        """Deactivate the plugin and disconnect window signals."""
        for handler_id in self.window.smart_autosave_plugin_handler_ids:
            self.window.disconnect(handler_id)

    def active_tab_changed(self, window, _new_tab):
        """Handle active tab change event."""
        maybe_save(window)

    def focus_out(self, window, _event):
        """Handle focus out event."""
        maybe_save(window)

    def tab_removed(self, window, tab):
        """Handle tab removed event and prompt to save unsaved documents."""
        if not self.is_closing:
            document = tab.get_document()
            file = document.get_file()
            if file and file.get_location() and ".gedit" in file.get_location().get_path():
                dialog = Gtk.MessageDialog(
                    transient_for=self.window,
                    flags=0,
                    message_type=Gtk.MessageType.QUESTION,
                    buttons=Gtk.ButtonsType.YES_NO,
                    text="Salvar documento?",
                )
                dialog.format_secondary_text(
                    "Você deseja salvar as alterações feitas no documento?"
                )
                response = dialog.run()
                if response == Gtk.ResponseType.NO:
                    try:
                        file_path = file.get_location().get_path()
                        subprocess.run(["gio", "trash", file_path])
                    except Exception as e:
                        print(f"Erro ao mover o arquivo para a lixeira: {e}")
                dialog.destroy()

    def on_window_delete_event(self, window, event):
        """Handle window delete event."""
        self.is_closing = True

    def on_window_show(self, window, data=None):
        """Restore tabs if this window is the first Gedit window instance."""
        if self._is_first_window():
            self.restore_tabs(window)

    def _is_first_window(self):
        """Return True if the window being added is the first window instance."""
        app = Gedit.App.get_default()
        return len(app.get_windows()) <= 1

    def restore_tabs(self, window):
        """Restore tabs from the temporary folder."""
        folder_path = os.path.expanduser(TMP_FOLDER)
        if os.path.isdir(folder_path):
            locations = []
            for filename in os.listdir(folder_path):
                if filename.endswith('.txt') or filename.endswith('.md'):
                    uri = os.path.join(folder_path, filename)
                    location = Gio.file_new_for_uri(f"file://{uri}")
                    if location.query_exists():
                        locations.append(location)
            
            if locations:
                locations.sort()
                Gedit.commands_load_locations(window, locations, None, 0, 0)
                documents = window.get_documents()
                if documents:
                    window.set_active_tab(Gedit.Tab.get_from_document(documents[0]))


def maybe_save(window):
    """Save unsaved documents in the window."""
    for document in window.get_unsaved_documents():
        file = document.get_file()
        if file.is_readonly():
            continue
        if file.is_externally_modified():
            continue
        if not file.get_location():
            save_path = os.path.expanduser(TMP_FOLDER)
            os.makedirs(save_path, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_file_name = f"{timestamp}.txt"
            temp_file_path = os.path.join(save_path, temp_file_name)
            file.set_location(Gio.File.new_for_path(temp_file_path))
        if not file.is_local():
            continue
        if not document.get_modified():
            continue
        Gedit.commands_save_document_async(document, window)
