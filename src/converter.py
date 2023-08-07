import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import subprocess
import os
import json

PREFERENCES_FILE = '.converter.json'


def save_preferences(prefs):
    with open(PREFERENCES_FILE, 'w') as file:
        json.dump(prefs, file)


def load_preferences():
    if os.path.exists(PREFERENCES_FILE):
        with open(PREFERENCES_FILE, 'r') as file:
            return json.load(file)
    return {'file_directory': '/', 'selected_directory': '/'}


def select_files():
    files = filedialog.askopenfilenames(initialdir=preferences['file_directory'], title='Select Files',
                                        filetypes=[(
                                            "Audio files",
                                            "*.aac;*.m4a;*.flac;*.mp3;*.opus;*.ogg;*.wav;*.ac3;*.alac;*.ape;*.au"
                                            ";*.caf;*.dts;*.gsm;*.mka;*.mlp;*.mp2;*.mpc;*.ra;*.spx;*.tta;*.voc;*.w64"
                                            ";*.wma"
                                        )])
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


def convert_files():
    directory = directory_entry.get()
    files = file_list.get(0, tk.END)
    format_option = format_var.get()
    output_format, bitrate_option = format_option.split(' - ') if 'kbps' in format_option else (format_option, None)

    if bitrate_option:
        bitrate_option = bitrate_option.replace('kbps', 'k')  # Removing "kbps" suffix

    progress_bar['maximum'] = len(files)
    progress_bar['value'] = 0

    for file in files:
        output_file = os.path.join(directory, file.split('/')[-1].rsplit('.', 1)[0] + '.' + output_format)
        if os.path.isfile(output_file):
            progress_bar['value'] += 1
            root.update_idletasks()
            continue
        command = ['ffmpeg', '-i', file, '-map_metadata', '0', '-y']

        if output_format == 'mp3' and bitrate_option:
            command += ['-b:a', bitrate_option]

        command.append(output_file)
        subprocess.run(command)
        progress_bar['value'] += 1
        root.update_idletasks()

    progress_bar['value'] = 0


preferences = load_preferences()

root = tk.Tk()
root.title('Audio File Converter')

select_button = tk.Button(root, text='Select Files', command=select_files)
select_button.pack()

file_list = tk.Listbox(root)
file_list.pack(fill=tk.BOTH, expand=tk.YES)

select_directory_button = tk.Button(root, text='Select Directory', command=select_directory)
select_directory_button.pack()

directory_entry = tk.Entry(root)  # Single-line entry widget for editing the selected directory
directory_entry.pack(fill=tk.X)
directory_entry.insert(0, preferences['selected_directory'])  # Set the initial value from preferences

format_var = tk.StringVar(root)
format_var.set('wav')  # default value
format_menu = tk.OptionMenu(root, format_var, 'mp3 - 320kbps', 'mp3 - 192kbps', 'flac', 'wav')
format_menu.pack()

convert_button = tk.Button(root, text='Convert Files', command=convert_files)
convert_button.pack()

progress_bar = ttk.Progressbar(root, orient='horizontal', length=200, mode='determinate')
progress_bar.pack()

root.mainloop()
