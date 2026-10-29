import csv
import queue
import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from . import VERSION
from .planning import import_pdf
from .engine import Engine


def main():
    root = tk.Tk()
    root.title(f'Plano de Ensino SEDUC-CE {VERSION}')
    root.geometry('900x750')
    root.minsize(650, 500)
    area = ttk.Frame(root, padding=12)
    area.pack(fill='both', expand=True)
    values = {k:tk.StringVar(value=v) for k,v in {
        'year':'2026', 'grade':'9', 'subject':'MATEMÁTICA', 'period':'1', 'pdf':'', 'excluded':''}.items()}
    labels = [('Ano letivo','year',None), ('Turma (ano escolar)','grade',['8','9']),
              ('Disciplina','subject',['MATEMÁTICA','IMERSÃO EM MATEMÁTICA']),
              ('Bimestre','period',['1','2','3','4'])]
    for row,(label,key,options) in enumerate(labels):
        ttk.Label(area,text=label).grid(row=row,column=0,sticky='w',pady=4)
        widget = ttk.Combobox(area,textvariable=values[key],values=options,state='readonly') if options else ttk.Entry(area,textvariable=values[key])
        widget.grid(row=row,column=1,sticky='ew',pady=4)
    def choose():
        name = filedialog.askopenfilename(filetypes=[('Alinhamento PDF','*.pdf')])
        if name:
            values['pdf'].set(name)
    ttk.Button(area,text='Escolher alinhamento PDF',command=choose).grid(row=4,column=0,sticky='w',pady=5)
    ttk.Entry(area,textvariable=values['pdf']).grid(row=4,column=1,sticky='ew')
    ttk.Label(area,text='Dias sem aula (DD/MM/AAAA, separados por vírgula)').grid(row=5,column=0,columnspan=2,sticky='w')
    ttk.Entry(area,textvariable=values['excluded']).grid(row=6,column=0,columnspan=2,sticky='ew')
    ttk.Label(area,text='Encontros: quarta e quinta. As datas vêm do PDF. Faça o login na janela do Chrome aberta pelo programa.').grid(row=7,column=0,columnspan=2,sticky='w',pady=8)
    buttons=ttk.Frame(area)
    buttons.grid(row=8,column=0,columnspan=2,sticky='ew')
    pane=ttk.Panedwindow(area,orient='vertical')
    pane.grid(row=9,column=0,columnspan=2,sticky='nsew',pady=8)
    frame=ttk.Frame(pane)
    preview=ttk.Treeview(frame,columns=('date','content','sub'),show='headings',height=10)
    for key,title,width in [('date','Data',90),('content','Conteúdo',230),('sub','Subconteúdo',460)]:
        preview.heading(key,text=title)
        preview.column(key,width=width,minwidth=70)
    preview.grid(row=0,column=0,sticky='nsew')
    scroll=ttk.Scrollbar(frame,orient='vertical',command=preview.yview)
    scroll.grid(row=0,column=1,sticky='ns')
    horizontal=ttk.Scrollbar(frame,orient='horizontal',command=preview.xview)
    horizontal.grid(row=1,column=0,sticky='ew')
    preview.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set)
    frame.rowconfigure(0,weight=1)
    frame.columnconfigure(0,weight=1)
    pane.add(frame,weight=3)
    log=tk.Text(pane,height=8,wrap='word',state='disabled')
    pane.add(log,weight=1)
    area.columnconfigure(1,weight=1)
    area.rowconfigure(9,weight=1)
    stop,resume=threading.Event(),threading.Event()
    messages=queue.Queue()
    current={'entries':[], 'thread':None}
    def append(msg):
        log.configure(state='normal')
        log.insert('end',msg+'\n')
        log.see('end')
        log.configure(state='disabled')
    def config():
        return {'year':int(values['year'].get()), 'grade':int(values['grade'].get()),
                'subject':values['subject'].get(), 'period':int(values['period'].get())}
    def load():
        cfg=config()
        excluded=[]
        for item in values['excluded'].get().split(','):
            if item.strip():
                d,m,y=map(int,item.strip().split('/'))
                excluded.append(date(y,m,d))
        if not values['pdf'].get():
            raise ValueError('Selecione o PDF do alinhamento.')
        current['entries']=import_pdf(values['pdf'].get(),cfg['year'],cfg['grade'],cfg['period'],excluded)
        if not current['entries']:
            raise ValueError('Nenhum encontro de quarta ou quinta encontrado.')
        preview.delete(*preview.get_children())
        for entry in current['entries']:
            preview.insert('', 'end',values=(entry.day.strftime('%d/%m/%Y'),entry.content,entry.subcontent))
        append(f"{len(current['entries'])} encontros preparados a partir do PDF.")
        return cfg
    def prepare():
        try:
            load()
        except Exception as e:
            messagebox.showerror('Importação do PDF',str(e))
    def start():
        if current['thread'] and current['thread'].is_alive():
            messagebox.showinfo('Programa em execução','Pare e feche a sessão do programa antes de iniciar outro lote.')
            return
        try:
            cfg=load()
        except Exception as e:
            messagebox.showerror('Preparação',str(e))
            return
        stop.clear()
        resume.clear()
        engine=Engine(cfg,list(current['entries']),messages.put,stop,resume)
        def run():
            try:
                engine.run()
            except Exception:
                messages.put('Não foi possível abrir o Chrome. Verifique se o Google Chrome está instalado.')
        current['thread']=threading.Thread(target=run,daemon=True)
        current['thread'].start()
    def export():
        try:
            load()
            path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('Planilha CSV','*.csv')])
            if path:
                with open(path,'w',encoding='utf-8-sig',newline='') as f:
                    writer=csv.writer(f,delimiter=';')
                    writer.writerow(['Data','Conteúdo','Subconteúdo'])
                    for e in current['entries']:
                        writer.writerow([e.day.strftime('%d/%m/%Y'),e.content,e.subcontent])
        except Exception as e:
            messagebox.showerror('Exportar',str(e))
    for index,(label,cmd) in enumerate([('Ler PDF',prepare),('Exportar CSV',export),('Iniciar',start),('Continuar após login',resume.set),('Parar e fechar sessão',stop.set)]):
        ttk.Button(buttons,text=label,command=cmd).grid(row=index//3,column=index%3,sticky='ew',padx=2,pady=2)
    for index in range(3):
        buttons.columnconfigure(index,weight=1)
    def poll():
        while not messages.empty():
            append(messages.get_nowait())
        root.after(200,poll)
    def close():
        stop.set()
        root.withdraw()
        def finish():
            worker = current['thread']
            if worker and worker.is_alive():
                root.after(100,finish)
            else:
                root.destroy()
        finish()
    root.protocol('WM_DELETE_WINDOW',close)
    poll()
    root.mainloop()
