"""Utility to shrink JPEG ditigal photos under a given directory if they are larger than a given resolution. Useful if
you want to keep old photos, but save space too."""
import argh
import os
from PIL import Image
import multiprocessing
import sys


class ProgressCounter(object):
    def __init__(self, total_items):
        self.total_items = total_items
        self.current_item = multiprocessing.RawValue('i', 0)
        self.lock = multiprocessing.Lock()

    def update(self):
        with self.lock:
            self.current_item.value += 1
            if self.current_item.value % 25 == 0:
                sys.stdout.write("\rProgress: {} of {} files processed.".format(self.current_item.value,
                                                                                self.total_items))
            elif self.current_item.value == self.total_items:
                sys.stdout.write("\rProgress: {} of {} files processed.\n".format(self.current_item.value,
                                                                                  self.total_items))


def main(path, width, height, quality=100):
    path = os.path.abspath(os.path.expanduser(path))
    size = (int(width), int(height))
    queue = multiprocessing.JoinableQueue()
    print("WARNING: This operation is destructive. Resized files under the path '{}' will be overwritten. Do not "
          "continue if you wish to preserve the original images.".format(path))
    response = input("If you understand and wish to continue, please type 'yes': ")
    if response == 'yes':
        num_files = add_jobs(queue, path)
        progress_bar = ProgressCounter(num_files)
        create_processes(multiprocessing.cpu_count(), queue, size, quality, progress_bar)
        try:
            queue.join()
        except KeyboardInterrupt:
            print("\nCanceled by keyboard interrupt.")
        print("Done!")
    else:
        print("Aborted resize directory.")
        sys.exit()


def add_jobs(queue, path):
    count = 0
    print("Adding jobs to queue...")
    for root, dirs, files in os.walk(path):
        for filename in files:
            count += 1
            queue.put(os.path.join(root, filename))
    return count


def create_processes(concurrency, queue, size, quality, progressbar):
    print("Creating {} worker processes...".format(concurrency))
    for n in range(concurrency):
        process = multiprocessing.Process(target=resize_worker, args=(queue, size, quality, progressbar))
        process.daemon = True
        process.start()


def resize_worker(queue, size, quality, progressbar):
    while True:
        try:
            filepath = queue.get()
            progressbar.update()
            try:
                resize_one(filepath, size, quality)
            except Exception as e:
                with open('resizedir.log', 'a') as f:
                    f.write(str(e) + '\n')
        finally:
            queue.task_done()


def resize_one(filepath, size, quality):
    with Image.open(filepath) as img:
        if img.format == 'JPEG' and img.size > size:
            img.thumbnail(size, Image.ANTIALIAS)
            img.save(filepath, "JPEG", quality=quality)


if __name__ == "__main__":
    argh.dispatch_command(main)
