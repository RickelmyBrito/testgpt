import datetime as dt
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from desktop.engine import AutomationError, register_month
from desktop.planning import CONTENT, METHOD, lessons


class App:
    def __init__(self, root):
        self.root = root
        self.stop = threading.Event()
        self.events = queue.Queue()
        self.worker = None
        root.title('Registro de Aulas — SEDUC-PI')
        root.geometry('760x' + str(min(850, max(500, root.winfo_screenheight() - 100))))
        root.minsize(640, 500)
        root.protocol('WM_DELETE_WINDOW', self.close)
        container = ttk.Frame(root)
        container.pack(fill='both', expand=True)
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        outer = ttk.Frame(canvas, padding=16)
        window = canvas.create_window((0, 0), window=outer, anchor='nw')
        outer.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(window, width=event.width))
        outer.columnconfigure(1, weight=1)
        self.fields = {}
        rows = [('usuario', 'Usuário', ''), ('senha', 'Senha', ''),
                ('escola', 'Escola (nome completo)', 'CETI AUGUSTINHO BRANDAO'),
                ('turma', 'Turma (nome completo)', ''), ('disciplina', 'Disciplina', 'MATEMÁTICA'),
                ('mes', 'Mês e ano (AAAA-MM)', dt.date.today().strftime('%Y-%m'))]
        for row, (name, title, value) in enumerate(rows):
            ttk.Label(outer, text=title).grid(row=row, column=0, sticky='w', pady=4)
            entry = ttk.Entry(outer, show='•' if name == 'senha' else '')
            entry.insert(0, value)
            entry.grid(row=row, column=1, sticky='ew', pady=4)
            self.fields[name] = entry
        ttk.Label(outer, text='Dias e horários — exemplo: 08:00 - 09:00; 10:00 - 11:00').grid(row=6, column=0, columnspan=2, sticky='w', pady=(12, 4))
        self.week = {}
        for row, (day, title) in enumerate([(1, 'Segunda'), (2, 'Terça'), (3, 'Quarta'), (4, 'Quinta'), (5, 'Sexta'), (6, 'Sábado'), (0, 'Domingo')], 7):
            enabled = tk.BooleanVar()
            ttk.Checkbutton(outer, text=title, variable=enabled).grid(row=row, column=0, sticky='w')
            entry = ttk.Entry(outer)
            entry.grid(row=row, column=1, sticky='ew', pady=2)
            self.week[day] = (enabled, entry)
        ttk.Label(outer, text='Dias sem aula no mês (ex.: 7, 12, 21)').grid(row=14, column=0, columnspan=2, sticky='w', pady=(12, 4))
        self.excluded = ttk.Entry(outer)
        self.excluded.grid(row=15, column=0, columnspan=2, sticky='ew')
        ttk.Label(outer, text='Conteúdo abordado').grid(row=16, column=0, columnspan=2, sticky='w', pady=(12, 4))
        self.content = tk.Text(outer, height=3, wrap='word')
        self.content.insert('1.0', CONTENT)
        self.content.grid(row=17, column=0, columnspan=2, sticky='ew')
        ttk.Label(outer, text='Metodologia').grid(row=18, column=0, columnspan=2, sticky='w', pady=(8, 4))
        self.method = tk.Text(outer, height=3, wrap='word')
        self.method.insert('1.0', METHOD)
        self.method.grid(row=19, column=0, columnspan=2, sticky='ew')
        ttk.Label(outer, text='Ao iniciar, o programa salva automaticamente e avança pela frequência mantendo os valores exibidos.\nUse textos correspondentes às aulas realizadas. Senha e sessão não são salvas pelo programa.', wraplength=700).grid(row=20, column=0, columnspan=2, sticky='w', pady=10)
        buttons = ttk.Frame(outer)
        buttons.grid(row=21, column=0, columnspan=2, sticky='ew')
        self.start_button = ttk.Button(buttons, text='Entrar e registrar mês', command=self.start)
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(buttons, text='Parar e fechar Chrome', command=self.stop.set, state='disabled')
        self.stop_button.pack(side='left', padx=8)
        self.output = tk.Text(outer, height=8, wrap='word', state='disabled')
        self.output.grid(row=22, column=0, columnspan=2, sticky='nsew', pady=(12, 0))
        outer.rowconfigure(22, weight=1)
        self.root.after(150, self.poll)

    def start(self):
        config = {name: field.get().strip() for name, field in self.fields.items() if name not in ('usuario', 'senha')}
        config.update(semana={str(day): entry.get().strip() for day, (enabled, entry) in self.week.items() if enabled.get()},
                      excecoes=self.excluded.get(), conteudo=self.content.get('1.0', 'end').strip(), metodologia=self.method.get('1.0', 'end').strip())
        username = self.fields['usuario'].get().strip()
        password = self.fields['senha'].get()
        try:
            if not username or not password:
                raise ValueError('Informe usuário e senha diretamente neste programa.')
            planned = lessons(config)
        except ValueError as error:
            messagebox.showerror('Confira os campos', str(error))
            return
        self.fields['senha'].delete(0, 'end')
        self.stop.clear()
        self.start_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.events.put(str(len(planned)) + ' aula(s) previstas. Iniciando…')

        def work():
            try:
                register_month(config, username, password, self.stop, self.events.put)
            except AutomationError as error:
                self.events.put(str(error))
            except Exception:
                self.events.put('Não foi possível iniciar. Verifique a instalação do programa e do Google Chrome.')
            finally:
                self.events.put(None)

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def poll(self):
        try:
            while True:
                text = self.events.get_nowait()
                if text is None:
                    self.start_button.configure(state='normal')
                    self.stop_button.configure(state='disabled')
                else:
                    self.output.configure(state='normal')
                    self.output.insert('end', text + '\n')
                    self.output.see('end')
                    self.output.configure(state='disabled')
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def close(self):
        if self.worker and self.worker.is_alive():
            self.stop.set()
            self.events.put('Encerrando a automação. Aguarde a janela do Chrome fechar.')
            self.root.after(300, self.close_when_stopped)
        else:
            self.root.destroy()

    def close_when_stopped(self):
        if self.worker and self.worker.is_alive():
            self.root.after(300, self.close_when_stopped)
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
