import os

exe_dir = r"D:\GIT\OptiCORD v2 (Development)\exe\main"
export_dir = r"C:\Users\gregor1\OneDrive - Office for National Statistics\Shared with Everyone\OptiCORD"

if __name__ == "__main__":
    os.chdir(exe_dir)
    for file in os.listdir(exe_dir):
        filename = os.fsdecode(file)
        # hide files that aren't the exe
        if not filename.endswith('.exe'):
            print(f'hiding {file}...')
            os.system(f'attrib +h {file}')
