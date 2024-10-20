import wx
import wx.adv
import wx.html
import subprocess
import os
import threading
import queue
import json
import webbrowser
import requests

def run_subprocess(cmd, output_queue):
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            output_queue.put(line)
        process.wait()
        if process.returncode == 0:
            output_queue.put("Process completed successfully!")
        else:
            output_queue.put(f"Process failed with return code {process.returncode}")
    except Exception as e:
        output_queue.put(f"An error occurred: {str(e)}")

def update_output(output_text, output_queue):
    try:
        while True:
            line = output_queue.get_nowait()
            if wx.Window.FindWindowById(output_text.GetId()):
                wx.CallAfter(output_text.AppendText, line)
            else:
                return  # Exit if the text control no longer exists
    except queue.Empty:
        pass
    except RuntimeError:
        return  # Exit if a RuntimeError occurs (e.g., window closed)
    wx.CallLater(100, update_output, output_text, output_queue)

def open_store_folder(folder_path):
    if os.path.exists(folder_path):
        os.startfile(folder_path)
    else:
        wx.MessageBox(f"The folder {folder_path} does not exist.", "Error", wx.OK | wx.ICON_ERROR)

class DarkThemedTextCtrl(wx.TextCtrl):
    def __init__(self, parent, id=wx.ID_ANY, value="", style=0):
        super().__init__(parent, id, value, style=style | wx.NO_BORDER)
        self.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.SetForegroundColour(wx.WHITE)

class CollapsiblePanel(wx.Panel):
    def __init__(self, parent, title, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.SetBackgroundColour(parent.GetBackgroundColour())
        
        self.toggle_button = wx.Button(self, label=title, style=wx.NO_BORDER)
        self.toggle_button.SetBackgroundColour(self.GetBackgroundColour())
        self.toggle_button.Bind(wx.EVT_BUTTON, self.on_toggle)
        
        self.content_panel = wx.Panel(self)
        self.content_panel.SetBackgroundColour(self.GetBackgroundColour())
        
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.toggle_button, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.content_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(self.main_sizer)
        self.collapsed = True
        self.toggle_button.SetLabel(f"▶ {title}")
        self.content_panel.Hide()
        
    def on_toggle(self, event):
        self.collapsed = not self.collapsed
        self.toggle_button.SetLabel(f"{'▶' if self.collapsed else '▼'} {self.toggle_button.GetLabel()[2:]}")
        self.content_panel.Show(not self.collapsed)
        self.Layout()
        self.GetParent().Layout()
        
    def get_content_panel(self):
        return self.content_panel

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Music Source Separation Training & Inference GUI")
        self.SetSize(994, 670)
        self.SetBackgroundColour(wx.Colour(247, 248, 250))  # #F7F8FA
        
        icon = wx.Icon("gui/favicon.ico", wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        # Center the window on the screen
        self.Center()

        # Set Poppins font for the entire application
        font_path = "gui/Poppins Regular 400.ttf"
        bold_font_path = "gui/Poppins Bold 700.ttf"
        wx.Font.AddPrivateFont(font_path)
        wx.Font.AddPrivateFont(bold_font_path)
        self.font = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Poppins")
        self.bold_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "Poppins")
        self.SetFont(self.font)

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Add image (with error handling)
        try:
            img = wx.Image("gui/mvsep.png", wx.BITMAP_TYPE_PNG)
            img_bitmap = wx.Bitmap(img)
            img_ctrl = wx.StaticBitmap(panel, -1, img_bitmap)
            main_sizer.Add(img_ctrl, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        except:
            print("Failed to load image: gui/mvsep.png")

        # Add title text
        title_text = wx.StaticText(panel, label="Music Source Separation Training && Inference GUI")
        title_text.SetFont(self.bold_font)
        title_text.SetForegroundColour(wx.BLACK)
        main_sizer.Add(title_text, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        # Add subtitle text
        subtitle_text = wx.StaticText(panel, label="Code by ZFTurbo / GUI by Bas Curtiz")
        subtitle_text.SetForegroundColour(wx.BLACK)
        main_sizer.Add(subtitle_text, 0, wx.ALIGN_CENTER | wx.TOP, 5)

        # Add GitHub link
        github_link = wx.adv.HyperlinkCtrl(panel, -1, "GitHub Repository", "https://github.com/ZFTurbo/Music-Source-Separation-Training")
        github_link.SetNormalColour(wx.Colour(1, 118, 179))  # #0176B3
        github_link.SetHoverColour(wx.Colour(86, 91, 123))  # #565B7B
        main_sizer.Add(github_link, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        # Add Download models button on a new line with 10px bottom margin
        download_models_btn = self.create_styled_button(panel, "Download Models", self.on_download_models)
        main_sizer.Add(download_models_btn, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)

        # Training Configuration
        self.training_panel = CollapsiblePanel(panel, "Training Configuration")
        self.training_panel.toggle_button.SetFont(self.bold_font)
        self.create_training_controls(self.training_panel.get_content_panel())
        main_sizer.Add(self.training_panel, 0, wx.EXPAND | wx.ALL, 10)

        # Inference Configuration
        self.inference_panel = CollapsiblePanel(panel, "Inference Configuration")
        self.inference_panel.toggle_button.SetFont(self.bold_font)
        self.create_inference_controls(self.inference_panel.get_content_panel())
        main_sizer.Add(self.inference_panel, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)
        self.load_settings()

    def create_styled_button(self, parent, label, handler):
        btn = wx.Button(parent, label=label, style=wx.BORDER_NONE)
        btn.SetBackgroundColour(wx.Colour(1, 118, 179))  # #0176B3
        btn.SetForegroundColour(wx.WHITE)
        btn.SetFont(self.bold_font)
        
        def on_enter(event):
            btn.SetBackgroundColour(wx.Colour(86, 91, 123))
            event.Skip()
        
        def on_leave(event):
            btn.SetBackgroundColour(wx.Colour(1, 118, 179))
            event.Skip()
        
        def on_click(event):
            btn.SetBackgroundColour(wx.Colour(86, 91, 123))
            handler(event)
            wx.CallLater(100, lambda: btn.SetBackgroundColour(wx.Colour(1, 118, 179)))
        
        btn.Bind(wx.EVT_ENTER_WINDOW, on_enter)
        btn.Bind(wx.EVT_LEAVE_WINDOW, on_leave)
        btn.Bind(wx.EVT_BUTTON, on_click)
        
        return btn

    def create_training_controls(self, panel):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Model Type
        model_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_type_sizer.Add(wx.StaticText(panel, label="Model Type:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.model_type = wx.Choice(panel, choices=["mdx23c", "htdemucs", "segm_models", "mel_band_roformer", "bs_roformer"])
        self.model_type.SetFont(self.font)
        model_type_sizer.Add(self.model_type, 0, wx.LEFT, 5)
        sizer.Add(model_type_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Config Path
        self.config_entry = self.add_browse_control(panel, sizer, "Config Path:", is_folder=False, is_config=True)

        # Start Checkpoint
        self.checkpoint_entry = self.add_browse_control(panel, sizer, "Checkpoint:", is_folder=False, is_checkpoint=True)

        # Results Path
        self.result_path_entry = self.add_browse_control(panel, sizer, "Results Path:", is_folder=True)

        # Data Paths
        self.data_entry = self.add_browse_control(panel, sizer, "Data Paths (separated by ';'):", is_folder=True)

        # Validation Paths
        self.valid_entry = self.add_browse_control(panel, sizer, "Validation Paths (separated by ';'):", is_folder=True)

        # Number of Workers and Device IDs
        workers_device_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        workers_sizer = wx.BoxSizer(wx.HORIZONTAL)
        workers_sizer.Add(wx.StaticText(panel, label="Number of Workers:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.workers_entry = wx.TextCtrl(panel, value="4")
        self.workers_entry.SetFont(self.font)
        workers_sizer.Add(self.workers_entry, 0, wx.LEFT, 5)
        workers_device_sizer.Add(workers_sizer, 0, wx.EXPAND)
        
        device_sizer = wx.BoxSizer(wx.HORIZONTAL)
        device_sizer.Add(wx.StaticText(panel, label="Device IDs (comma-separated):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 20)
        self.device_entry = wx.TextCtrl(panel, value="0")
        self.device_entry.SetFont(self.font)
        device_sizer.Add(self.device_entry, 0, wx.LEFT, 5)
        workers_device_sizer.Add(device_sizer, 0, wx.EXPAND)
        
        sizer.Add(workers_device_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Run Training Button
        self.run_button = self.create_styled_button(panel, "Run Training", self.run_training)
        sizer.Add(self.run_button, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        panel.SetSizer(sizer)

    def create_inference_controls(self, panel):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Model Type
        infer_model_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        infer_model_type_sizer.Add(wx.StaticText(panel, label="Model Type:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.infer_model_type = wx.Choice(panel, choices=["mdx23c", "htdemucs", "segm_models", "mel_band_roformer", "bs_roformer"])
        self.infer_model_type.SetFont(self.font)
        infer_model_type_sizer.Add(self.infer_model_type, 0, wx.LEFT, 5)
        sizer.Add(infer_model_type_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Config Path
        self.infer_config_entry = self.add_browse_control(panel, sizer, "Config Path:", is_folder=False, is_config=True)

        # Start Checkpoint
        self.infer_checkpoint_entry = self.add_browse_control(panel, sizer, "Checkpoint:", is_folder=False, is_checkpoint=True)

        # Input Folder
        self.infer_input_entry = self.add_browse_control(panel, sizer, "Input Folder:", is_folder=True)

        # Store Directory
        self.infer_store_entry = self.add_browse_control(panel, sizer, "Output Folder:", is_folder=True)

        # Extract Instrumental Checkbox
        self.extract_instrumental_checkbox = wx.CheckBox(panel, label="Extract Instrumental")
        self.extract_instrumental_checkbox.SetFont(self.font)
        sizer.Add(self.extract_instrumental_checkbox, 0, wx.EXPAND | wx.ALL, 5)

        # Run Inference Button
        self.run_infer_button = self.create_styled_button(panel, "Run Inference", self.run_inference)
        sizer.Add(self.run_infer_button, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        panel.SetSizer(sizer)

    def add_browse_control(self, panel, sizer, label, is_folder=False, is_config=False, is_checkpoint=False):
        browse_sizer = wx.BoxSizer(wx.HORIZONTAL)
        browse_sizer.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        entry = wx.TextCtrl(panel)
        entry.SetFont(self.font)
        browse_sizer.Add(entry, 1, wx.EXPAND | wx.LEFT, 5)
        browse_button = self.create_styled_button(panel, "Browse", lambda event, entry=entry, is_folder=is_folder, is_config=is_config, is_checkpoint=is_checkpoint: self.browse(event, entry, is_folder, is_config, is_checkpoint))
        browse_sizer.Add(browse_button, 0, wx.LEFT, 5)
        sizer.Add(browse_sizer, 0, wx.EXPAND | wx.ALL, 5)
        return entry

    def browse(self, event, entry, is_folder=False, is_config=False, is_checkpoint=False):
        if is_folder:
            dialog = wx.DirDialog(self, "Choose a directory", style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        else:
            wildcard = "All files (*.*)|*.*"
            if is_config:
                wildcard = "YAML files (*.yaml)|*.yaml"
            elif is_checkpoint:
                wildcard = "Checkpoint files (*.bin;*.ckpt;*.th)|*.bin;*.ckpt;*.th"
            
            dialog = wx.FileDialog(self, "Choose a file", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST, wildcard=wildcard)
        
        dialog.SetFont(self.font)
        if dialog.ShowModal() == wx.ID_OK:
            entry.SetValue(dialog.GetPath())
        dialog.Destroy()

    def create_output_window(self, title, folder_path):
        output_frame = wx.Frame(self, title=title, style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
        output_frame.SetIcon(self.GetIcon())
        output_frame.SetSize(994, 670)
        output_frame.SetBackgroundColour(wx.Colour(0, 0, 0))
        output_frame.SetFont(self.font)
        
        # Set the position of the output frame to match the main frame
        output_frame.SetPosition(self.GetPosition())
        
        output_title = wx.StaticText(output_frame, label=title)
        output_title.SetFont(self.bold_font)
        output_title.SetForegroundColour(wx.WHITE)
        
        output_text = DarkThemedTextCtrl(output_frame, style=wx.TE_MULTILINE | wx.TE_READONLY)
        output_text.SetFont(self.font)
        
        open_folder_button = self.create_styled_button(output_frame, f"Open Output Folder", lambda event: open_store_folder(folder_path))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(output_title, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        sizer.Add(output_text, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(open_folder_button, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        output_frame.SetSizer(sizer)
        
        return output_frame, output_text

    def run_training(self, event):
        model_type = self.model_type.GetStringSelection()
        config_path = self.config_entry.GetValue()
        start_checkpoint = self.checkpoint_entry.GetValue()
        results_path = self.result_path_entry.GetValue()
        data_paths = self.data_entry.GetValue()
        valid_paths = self.valid_entry.GetValue()
        num_workers = self.workers_entry.GetValue()
        device_ids = self.device_entry.GetValue()

        if not model_type:
            wx.MessageBox("Please select a model type.", "Input Error", wx.OK | wx.ICON_ERROR)
            return
        if not config_path:
            wx.MessageBox("Please select a config file.", "Input Error", wx.OK | wx.ICON_ERROR)
            return
        if not results_path:
            wx.MessageBox("Please specify a results path.", "Input Error", wx.OK | wx.ICON_ERROR)
            return
        if not data_paths:
            wx.MessageBox("Please specify data paths.", "Input Error", wx.OK | wx.ICON_ERROR)
            return
        if not valid_paths:
            wx.MessageBox("Please specify validation paths.", "Input Error", wx.OK | wx.ICON_ERROR)
            return

        cmd = [
            "python", "train.py",
            "--model_type", model_type,
            "--config_path", config_path,
            "--results_path", results_path,
            "--data_path", *data_paths.split(';'),
            "--valid_path", *valid_paths.split(';'),
            "--num_workers", num_workers,
            "--device_ids", device_ids
        ]

        if start_checkpoint:
            cmd += ["--start_check_point", start_checkpoint]

        output_queue = queue.Queue()
        threading.Thread(target=run_subprocess, args=(cmd, output_queue), daemon=True).start()
        
        output_frame, output_text = self.create_output_window("Training Output", results_path)
        output_frame.Show()
        update_output(output_text, output_queue)

        self.save_settings()

    def run_inference(self, event):
        model_type = self.infer_model_type.GetStringSelection()
        config_path = self.infer_config_entry.GetValue()
        start_checkpoint = self.infer_checkpoint_entry.GetValue()
        input_folder = self.infer_input_entry.GetValue()
        store_dir = self.infer_store_entry.GetValue()
        extract_instrumental = self.extract_instrumental_checkbox.GetValue()

        if not model_type:
            wx.MessageBox("Please select a model type.", "Input Error", wx.OK | wx.ICON_ERROR)
            return
        if not config_path:
            wx.MessageBox("Please select a config file.", "Input Error", wx.OK | wx.ICON_ERROR)
            return
        if not input_folder:
            wx.MessageBox("Please specify an input folder.", "Input Error", wx.OK | wx.ICON_ERROR)
            return
        if not store_dir:
            wx.MessageBox("Please specify an output folder.", "Input Error", wx.OK | wx.ICON_ERROR)
            return

        cmd = [
            "python", "inference.py",
            "--model_type", model_type,
            "--config_path", config_path,
            "--input_folder", input_folder,
            "--store_dir", store_dir
        ]

        if start_checkpoint:
            cmd += ["--start_check_point", start_checkpoint]

        if extract_instrumental:
            cmd += ["--extract_instrumental"]

        output_queue = queue.Queue()
        threading.Thread(target=run_subprocess, args=(cmd, output_queue), daemon=True).start()
        
        output_frame, output_text = self.create_output_window("Inference Output", store_dir)
        output_frame.Show()
        update_output(output_text, output_queue)

        self.save_settings()

    def save_settings(self):
        settings = {
            "model_type": self.model_type.GetStringSelection(),
            "config_path": self.config_entry.GetValue(),
            "start_checkpoint": self.checkpoint_entry.GetValue(),
            "results_path": self.result_path_entry.GetValue(),
            "data_paths": self.data_entry.GetValue(),
            "valid_paths": self.valid_entry.GetValue(),
            "num_workers": self.workers_entry.GetValue(),
            "device_ids": self.device_entry.GetValue(),
            "infer_model_type": self.infer_model_type.GetStringSelection(),
            "infer_config_path": self.infer_config_entry.GetValue(),
            "infer_start_checkpoint": self.infer_checkpoint_entry.GetValue(),
            "infer_input_folder": self.infer_input_entry.GetValue(),
            "infer_store_dir": self.infer_store_entry.GetValue(),
            "extract_instrumental": self.extract_instrumental_checkbox.GetValue()
        }
        with open("settings.json", "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
            
            self.model_type.SetStringSelection(settings.get("model_type", ""))
            self.config_entry.SetValue(settings.get("config_path", ""))
            self.checkpoint_entry.SetValue(settings.get("start_checkpoint", ""))
            self.result_path_entry.SetValue(settings.get("results_path", ""))
            self.data_entry.SetValue(settings.get("data_paths", ""))
            self.valid_entry.SetValue(settings.get("valid_paths", ""))
            self.workers_entry.SetValue(settings.get("num_workers", "4"))
            self.device_entry.SetValue(settings.get("device_ids", "0"))
            
            self.infer_model_type.SetStringSelection(settings.get("infer_model_type", ""))
            self.infer_config_entry.SetValue(settings.get("infer_config_path", ""))
            self.infer_checkpoint_entry.SetValue(settings.get("infer_start_checkpoint", ""))
            self.infer_input_entry.SetValue(settings.get("infer_input_folder", ""))
            self.infer_store_entry.SetValue(settings.get("infer_store_dir", ""))
            self.extract_instrumental_checkbox.SetValue(settings.get("extract_instrumental", False))
        except FileNotFoundError:
            pass  # If the settings file doesn't exist, use default values

    def on_download_models(self, event):
        DownloadModelsFrame(self).Show()

class CustomHtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.SetStandardFonts(size=9, normal_face="Poppins", fixed_face="Poppins")

class DownloadModelsFrame(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, title="Download Models", size=(994, 670))
        self.SetBackgroundColour(wx.Colour(247, 248, 250))  # #F7F8FA
        self.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Poppins"))
        
        # Set the position of the Download Models frame to match the main frame
        self.SetPosition(parent.GetPosition())

        # Set the icon for the Download Models frame
        icon = wx.Icon("gui/favicon.ico", wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Add scrolled window
        scrolled_window = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        scrolled_window.SetScrollRate(0, 20)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        html_window = CustomHtmlWindow(scrolled_window, style=wx.html.HW_SCROLLBAR_AUTO)
        html_window.SetPage(self.get_content())
        html_window.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_click)
        scroll_sizer.Add(html_window, 1, wx.EXPAND | wx.ALL, 10)

        scrolled_window.SetSizer(scroll_sizer)
        sizer.Add(scrolled_window, 1, wx.EXPAND)
        panel.SetSizer(sizer)

    def get_content(self):
        try:
            response = requests.get("https://bascurtiz.x10.mx/models-checkpoint-config-urls.html")
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            return f"<html><body><p>An error occurred while fetching the content: {str(e)}</p></body></html>"

    def on_link_click(self, event):
        href = event.GetLinkInfo().GetHref()
        webbrowser.open(href)

if __name__ == "__main__":
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()
