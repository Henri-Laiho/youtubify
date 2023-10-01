from tkinter import ttk
from tkinter import filedialog
from threading import Thread
import tkinter as tk
import subprocess
import os
import json
import easygui

PREFERENCES_FILE = '.converter_data.json'


def save_preferences(prefs):
    with open(PREFERENCES_FILE, 'w') as file:
        json.dump(prefs, file)


def load_preferences():
    if os.path.exists(PREFERENCES_FILE):
        with open(PREFERENCES_FILE, 'r') as file:
            return json.load(file)
    return {'file_directory': '.', 'selected_directory': '.'}


def select_files():
    filetypes = [
        ["*.aac", "*.m4a", "*.flac", "*.mp3", "*.opus", "*.ogg", "*.wav", "*.ac3", "*.alac", "*.ape",
         "*.au", "*.caf", "*.dts", "*.gsm", "*.mka", "*.mlp", "*.mp2", "*.mpc", "*.ra", "*.spx", "*.tta",
         "*.voc", "*.w64", "*.wma", "Audio files"],
    ]
    files = easygui.fileopenbox(default=os.path.join(preferences['file_directory'], '*'), filetypes=filetypes,
                                multiple=True)

    file_list.delete(0, tk.END)
    for file in files:
        file_list.insert(tk.END, file)
    if files:
        preferences['file_directory'] = os.path.dirname(files[0])
        save_preferences(preferences)
    progress_bar['maximum'] = len(files)
    progress_bar['value'] = 0


def select_directory():
    directory = filedialog.askdirectory(initialdir=preferences['selected_directory'], title='Select Directory')
    directory_entry.delete(0, tk.END)
    directory_entry.insert(0, directory)
    preferences['selected_directory'] = directory
    save_preferences(preferences)


def convert_files_thread():
    directory = directory_entry.get()
    if not os.path.isdir(directory):
        os.makedirs(directory)
    files = file_list.get(0, tk.END)
    format_option = format_var.get()
    output_formats = format_option.split(' - ')
    output_format = output_formats[0]
    bitrate_option = None
    if 'kbps' in format_option:
        bitrate_option = output_formats[1]
    if bitrate_option:
        bitrate_option = bitrate_option.replace('kbps', 'k')  # Removing "kbps" suffix

    progress_bar['maximum'] = len(files)
    progress_bar['value'] = 0

    for file in files:
        output_file = os.path.join(directory, file.split(os.path.sep)[-1].rsplit('.', 1)[0] + '.' + output_format)
        if os.path.isfile(output_file):
            root.after(0, lambda value=progress_bar['value'] + 1: progress_bar.config(value=value))
            continue
        command = ['ffmpeg', '-i', file, '-map_metadata', '0', '-y']

        if output_format == 'mp3' and bitrate_option:
            command += ['-b:a', bitrate_option]
        elif format_option == 'wav - 22050Hz':
            command += ['-ar', '22050']

        command.append(output_file)
        subprocess.run(command)
        root.after(0, lambda value=progress_bar['value'] + 1: progress_bar.config(value=value))

    root.after(0, lambda: progress_bar.config(value=0))


def convert_files():
    thread = Thread(target=convert_files_thread)
    thread.start()


preferences = load_preferences()

root = tk.Tk()
root.title('Audio File Converter')

select_button = tk.Button(root, text='Select Files', command=select_files)
select_button.pack()

file_list = tk.Listbox(root)
file_list.pack(fill=tk.BOTH, expand=tk.YES)

select_directory_button = tk.Button(root, text='Select Output Directory', command=select_directory)
select_directory_button.pack()

directory_entry = tk.Entry(root)  # Single-line entry widget for editing the selected directory
directory_entry.pack(fill=tk.X)
directory_entry.insert(0, preferences['selected_directory'])  # Set the initial value from preferences

format_var = tk.StringVar(root)
format_var.set('wav')  # default value
format_menu = tk.OptionMenu(root, format_var, 'mp3 - 320kbps', 'mp3 - 192kbps', 'flac', 'wav', 'wav - 22050Hz')
format_menu.pack()

convert_button = tk.Button(root, text='Convert Files', command=convert_files)
convert_button.pack()

progress_bar = ttk.Progressbar(root, orient='horizontal', length=200, mode='determinate')
progress_bar.pack()

root.mainloop()
