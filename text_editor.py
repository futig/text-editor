import curses
import time

from client import Client


class TextEditor:
    def __init__(self, client):
        self.client = client
        self.text = client.document_text.split("\n")
        # self.prev_text = client.document_text
        self.cursor_x = 0
        self.cursor_y = 0
        self.history = []
        self.last_save_time = time.time()
        self.text_changed = False
        

    def sync_text(self):
        current_text = "\n".join(self.text)
        client.send_operations(current_text)
        # self.prev_text = current_text


    def Run(self, stdscr):
        curses.curs_set(1)  
        while True:
            if self.client.state_updated:
                self.text = self.client.document_text.split("\n")
            stdscr.clear()

            for idx, line in enumerate(self.text):
                stdscr.addstr(idx, 0, line)

            stdscr.move(self.cursor_y, self.cursor_x)
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP:
                self.cursor_y = max(0, self.cursor_y - 1)
                self.cursor_x = min(self.cursor_x, len(self.text[self.cursor_y]))
            elif key == curses.KEY_DOWN:
                self.cursor_y = min(len(self.text) - 1, self.cursor_y + 1)
                self.cursor_x = min(self.cursor_x, len(self.text[self.cursor_y]))
            elif key == curses.KEY_LEFT:
                self.cursor_x = max(0, self.cursor_x - 1)
            elif key == curses.KEY_RIGHT:
                self.cursor_x = min(len(self.text[self.cursor_y]), self.cursor_x + 1)

            
            elif key == curses.KEY_BACKSPACE or key == 127:
                self.text_changed = True
                if self.cursor_x > 0:
                    line = self.text[self.cursor_y]
                    self.text[self.cursor_y] = line[:self.cursor_x - 1] + line[self.cursor_x:]
                    self.cursor_x -= 1
                elif self.cursor_y > 0:
                    self.cursor_x = len(self.text[self.cursor_y - 1])
                    self.text[self.cursor_y - 1] += self.text[self.cursor_y]
                    del self.text[self.cursor_y]
                    self.cursor_y -= 1
            elif key == curses.KEY_ENTER or key == 10:
                self.text_changed = True
                line = self.text[self.cursor_y]
                new_line = line[self.cursor_x:]
                self.text[self.cursor_y] = line[:self.cursor_x]
                self.text.insert(self.cursor_y + 1, new_line)
                self.cursor_y += 1
                self.cursor_x = 0
            else:
                try:
                    ch = chr(key)
                    self.text_changed = True
                    line = self.text[self.cursor_y]
                    self.text[self.cursor_y] = line[:self.cursor_x] + ch + line[self.cursor_x:]
                    self.cursor_x += 1
                except:
                    pass  # Игнорируем неотображаемые символы
            
            if self.text_changed and time.time() - self.last_save_time > 1:
                self.sync_text()
                self.last_save_time = time.time()
                self.text_changed = False
            
            self.cursor_y = min(max(self.cursor_y, 0), len(self.text) - 1)
            self.cursor_x = min(max(self.cursor_x, 0), len(self.text[self.cursor_y]))


if __name__ == '__main__':
    client = Client()
    editor = TextEditor(client)
    curses.wrapper(editor.Run)
