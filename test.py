import curses

def main(stdscr):
    # Очищаем экран
    stdscr.clear()
    curses.curs_set(1)  # Показываем курсор

    # Инициализация переменных
    cursor_x = 0
    cursor_y = 0
    text = ['']
    max_y, max_x = stdscr.getmaxyx()

    while True:
        stdscr.clear()

        # Отображение текста
        for idx, line in enumerate(text):
            stdscr.addstr(idx, 0, line)

        stdscr.move(cursor_y, cursor_x)
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            if cursor_y > 0:
                cursor_y -= 1
                cursor_x = min(cursor_x, len(text[cursor_y]))
        elif key == curses.KEY_DOWN:
            if cursor_y + 1 < len(text):
                cursor_y += 1
                cursor_x = min(cursor_x, len(text[cursor_y]))
        elif key == curses.KEY_LEFT:
            if cursor_x > 0:
                cursor_x -= 1
            elif cursor_y > 0:
                cursor_y -= 1
                cursor_x = len(text[cursor_y])
        elif key == curses.KEY_RIGHT:
            if cursor_x < len(text[cursor_y]):
                cursor_x += 1
            elif cursor_y + 1 < len(text):
                cursor_y += 1
                cursor_x = 0
        elif key == curses.KEY_BACKSPACE or key == 127:
            if cursor_x > 0:
                line = text[cursor_y]
                text[cursor_y] = line[:cursor_x - 1] + line[cursor_x:]
                cursor_x -= 1
            elif cursor_y > 0:
                cursor_x = len(text[cursor_y - 1])
                text[cursor_y - 1] += text[cursor_y]
                del text[cursor_y]
                cursor_y -= 1
        elif key == curses.KEY_DC:
            line = text[cursor_y]
            if cursor_x < len(line):
                text[cursor_y] = line[:cursor_x] + line[cursor_x + 1:]
            elif cursor_y + 1 < len(text):
                text[cursor_y] += text[cursor_y + 1]
                del text[cursor_y + 1]
        elif key == curses.KEY_ENTER or key == 10:
            line = text[cursor_y]
            new_line = line[cursor_x:]
            text[cursor_y] = line[:cursor_x]
            text.insert(cursor_y + 1, new_line)
            cursor_y += 1
            cursor_x = 0
        elif key == 27:  # Клавиша Escape для выхода
            break
        else:
            # Добавляем символ в строку
            try:
                ch = chr(key)
                line = text[cursor_y]
                text[cursor_y] = line[:cursor_x] + ch + line[cursor_x:]
                cursor_x += 1
            except:
                pass  # Игнорируем неотображаемые символы

        # Обеспечиваем, что курсор остается в пределах
        cursor_y = min(max(cursor_y, 0), len(text) - 1)
        cursor_x = min(max(cursor_x, 0), len(text[cursor_y]))

if __name__ == '__main__':
    curses.wrapper(main)
