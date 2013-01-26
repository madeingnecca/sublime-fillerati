import sublime
import sublime_plugin
import threading
import urllib2
import json
import random


class FilleratiCommand(sublime_plugin.TextCommand):

    def run(self, edit, n=300, b=None):

        # Api url and books in config.
        settings = sublime.load_settings('Fillerati.sublime-settings')
        api_url = settings.get('api_url')
        books = settings.get('books')

        count = len(self.view.sel())
        completes = []

        def api_check(thread):
            # Not yet finished.
            if thread.result is None:
                sublime.set_timeout(lambda: api_check(thread), 100)
                return

            # Finished, with error.
            if thread.result is False:
                sublime.error_message(thread.error)
                return

            # Completed.
            completes.append(
                lambda r, n: self.complete(edit, r, thread.result, n))

            # Completed all threads. Replace!
            if (len(completes) == count):
                i = 0
                for region in self.view.sel():
                    # Character count from selection.
                    try:
                        cnt = int(self.view.substr(region))
                    except ValueError:
                        # Default parameter if no integer.
                        cnt = n
                    completes[i](region, cnt)
                    i += 1

        # Start all threads, process results once all have finished
        for region in self.view.sel():
            # If no book in param, choose random one.
            if b is None:
                book = random.choice(books.keys())
            else:
                book = b
            # Random paragraph.
            para = random.choice(range(books[book]))

            thread = FilleratiApiCall(api_url.format(book, para))

            thread.start()

            # Completion check
            api_check(thread)

    def complete(self, edit, region, result, n):

        paragraphs = ''.join(result['p'])
        content = paragraphs[:n]

        chapter = ''.join(result['ch'])

        if region.empty():
            self.view.insert(edit, region.begin(), content)
        else:
            self.view.replace(edit, region, content)

        sublime.status_message(chapter)


# Fillerati caller
class FilleratiApiCall(threading.Thread):

    def __init__(self, url, opts={}):

        self.url = url
        self.opts = opts
        self.result = None
        self.exception = None
        self.error = None
        threading.Thread.__init__(self)

    def run(self):

        # Do request and save in "result" field.
        try:
            request = urllib2.Request(self.url)
            http_file = urllib2.urlopen(request)
            response_raw = http_file.read()

            response_obj = json.loads(response_raw)
            self.result = response_obj
            return

        # Save error, notify api call has failed.
        except (urllib2.HTTPError) as (e):
            err = '%s: HTTP error %s contacting API' % (__name__, str(e.code))
            self.exception = e
        except (urllib2.URLError) as (e):
            err = '%s: URL error %s contacting API' % (__name__, str(e.reason))
            self.exception = e

        self.error = err
        self.result = False
