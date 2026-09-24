import sys, os, sqlite3, re
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QTextBrowser, QLineEdit, QPushButton,
    QSplitter, QFrame, QStatusBar, QMessageBox, QFileDialog, QToolBar,
    QComboBox, QCheckBox
)

APP_TITLE = "JASS Heer Waris Shah Explorer"
DB_NAME = "JASS_Heer_Waris_Shah.db"
PDF_NAME = "Heer_WarisShah_PunjabiLibrary.pdf"

class DB:
    def __init__(self, path):
        self.path = path
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row

    def sections(self, query=""):
        if not query.strip():
            return self.con.execute("SELECT section_no,title,start_page,end_page FROM sections ORDER BY section_no").fetchall()
        q = query.strip()
        try:
            return self.con.execute("""
                SELECT s.section_no,s.title,s.start_page,s.end_page
                FROM sections s JOIN sections_fts f ON f.rowid=s.section_id
                WHERE sections_fts MATCH ? ORDER BY s.section_no
            """, (q,)).fetchall()
        except sqlite3.Error:
            like = f"%{q}%"
            return self.con.execute("""SELECT section_no,title,start_page,end_page FROM sections
                WHERE title LIKE ? OR body LIKE ? OR notes LIKE ? ORDER BY section_no""", (like,like,like)).fetchall()

    def section(self, no):
        return self.con.execute("SELECT * FROM sections WHERE section_no=?", (no,)).fetchone()

    def verses(self, no):
        return self.con.execute("SELECT verse_no,text,source_page FROM verses WHERE section_no=? ORDER BY verse_no", (no,)).fetchall()

    def notes(self, no):
        return self.con.execute("SELECT note_id,note_text FROM notes WHERE section_no=? ORDER BY note_id", (no,)).fetchall()

    def search_verses(self, query):
        try:
            return self.con.execute("""
                SELECT v.section_no,v.verse_no,v.text,v.source_page,s.title
                FROM verses_fts f JOIN verses v ON f.rowid=v.verse_id
                JOIN sections s ON s.section_no=v.section_no
                WHERE verses_fts MATCH ? ORDER BY v.section_no,v.verse_no LIMIT 250
            """, (query,)).fetchall()
        except sqlite3.Error:
            q=f"%{query}%"
            return self.con.execute("""SELECT v.section_no,v.verse_no,v.text,v.source_page,s.title
                FROM verses v JOIN sections s ON s.section_no=v.section_no
                WHERE v.text LIKE ? ORDER BY v.section_no,v.verse_no LIMIT 250""", (q,)).fetchall()

    def metadata(self):
        return dict(self.con.execute("SELECT key,value FROM metadata" ).fetchall())

class Explorer(QMainWindow):
    def __init__(self, db_path):
        super().__init__()
        self.db = DB(db_path)
        self.current_no = None
        self.dark = True
        self.setWindowTitle(APP_TITLE)
        self.resize(1450, 900)
        self.setMinimumSize(1100, 700)
        self.build_ui()
        self.apply_theme()
        self.load_sections()
        if self.section_list.count():
            self.section_list.setCurrentRow(0)

    def build_ui(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(20,20))
        self.addToolBar(tb)
        title = QLabel("  JASS • HEER WARIS SHAH")
        title.setObjectName("toolbarTitle")
        tb.addWidget(title)
        tb.addSeparator()
        self.theme_btn = QPushButton("☾  Theme")
        self.theme_btn.clicked.connect(self.toggle_theme)
        tb.addWidget(self.theme_btn)
        self.open_pdf_btn = QPushButton("Open Source PDF")
        self.open_pdf_btn.clicked.connect(self.open_pdf)
        tb.addWidget(self.open_pdf_btn)

        root = QWidget(); root_layout = QVBoxLayout(root); root_layout.setContentsMargins(18,14,18,12); root_layout.setSpacing(12)
        hero = QFrame(); hero.setObjectName("hero")
        hl = QVBoxLayout(hero); hl.setContentsMargins(24,20,24,20)
        self.hero_title = QLabel("ਹੀਰ ਵਾਰਿਸ ਸ਼ਾਹ")
        self.hero_title.setObjectName("heroTitle")
        self.hero_sub = QLabel("Waris Shah  •  Punjabi Qissa  •  Gurmukhi Explorer")
        self.hero_sub.setObjectName("heroSub")
        hl.addWidget(self.hero_title); hl.addWidget(self.hero_sub)
        root_layout.addWidget(hero)

        search_row = QHBoxLayout(); search_row.setSpacing(8)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search sections and verses…  (Punjabi or English)")
        self.search.setClearButtonEnabled(True); self.search.returnPressed.connect(self.run_search)
        search_row.addWidget(self.search, 1)
        b = QPushButton("Search"); b.clicked.connect(self.run_search); search_row.addWidget(b)
        self.all_btn = QPushButton("All Sections"); self.all_btn.clicked.connect(lambda: (self.search.clear(), self.load_sections()))
        search_row.addWidget(self.all_btn)
        root_layout.addLayout(search_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        left = QFrame(); left.setObjectName("panel")
        ll = QVBoxLayout(left); ll.setContentsMargins(12,12,12,12)
        head = QHBoxLayout()
        self.section_label = QLabel("SECTIONS")
        self.section_label.setObjectName("panelTitle")
        head.addWidget(self.section_label); head.addStretch()
        self.count_label = QLabel(""); self.count_label.setObjectName("muted")
        head.addWidget(self.count_label)
        ll.addLayout(head)
        self.section_list = QListWidget(); self.section_list.setObjectName("sectionList")
        self.section_list.currentItemChanged.connect(self.section_changed)
        ll.addWidget(self.section_list)
        splitter.addWidget(left)

        center = QFrame(); center.setObjectName("panel")
        cl = QVBoxLayout(center); cl.setContentsMargins(22,18,22,18); cl.setSpacing(10)
        self.section_no = QLabel(""); self.section_no.setObjectName("sectionNo")
        self.section_title = QLabel("Select a section"); self.section_title.setObjectName("sectionTitle")
        self.section_title.setWordWrap(True)
        self.page_label = QLabel(""); self.page_label.setObjectName("muted")
        cl.addWidget(self.section_no); cl.addWidget(self.section_title); cl.addWidget(self.page_label)
        self.rule = QFrame(); self.rule.setFrameShape(QFrame.HLine); self.rule.setObjectName("rule"); cl.addWidget(self.rule)
        self.verses = QTextBrowser(); self.verses.setObjectName("verseView"); self.verses.setOpenExternalLinks(False)
        cl.addWidget(self.verses, 1)
        splitter.addWidget(center)

        right = QFrame(); right.setObjectName("panel")
        rl = QVBoxLayout(right); rl.setContentsMargins(18,18,18,18)
        nt = QLabel("NOTES & SOURCE"); nt.setObjectName("panelTitle"); rl.addWidget(nt)
        self.notes = QTextBrowser(); self.notes.setObjectName("notesView"); rl.addWidget(self.notes, 1)
        self.source = QLabel(""); self.source.setWordWrap(True); self.source.setObjectName("sourceCard"); rl.addWidget(self.source)
        splitter.addWidget(right)
        splitter.setSizes([310,700,340])
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(root)
        self.add_shortcuts()

    def add_shortcuts(self):
        act = QAction(self); act.setShortcut("Ctrl+F"); act.triggered.connect(lambda: self.search.setFocus()); self.addAction(act)
        act2 = QAction(self); act2.setShortcut("Esc"); act2.triggered.connect(self.search.clear); self.addAction(act2)

    def apply_theme(self):
        if self.dark:
            self.setStyleSheet("""
            QWidget{background:#0b1020;color:#e9edf5;font-family:'Noto Sans','Nirmala UI',sans-serif;}
            QToolBar{background:#080c17;border:0;padding:8px 10px;}
            #toolbarTitle{font-weight:800;letter-spacing:1px;color:#f2c66d;font-size:14px;}
            #hero{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #151c32,stop:1 #26314d);border:1px solid #394867;border-radius:18px;}
            #heroTitle{font-family:'Noto Sans Gurmukhi','Nirmala UI';font-size:36px;font-weight:800;color:#f6d486;}
            #heroSub{font-size:14px;color:#aeb9cf;}
            #panel{background:#11182a;border:1px solid #27334b;border-radius:16px;}
            #panelTitle{font-size:12px;font-weight:800;letter-spacing:1.5px;color:#8fa0bd;}
            #muted{color:#71809b;font-size:12px;}
            QLineEdit{background:#0f1626;border:1px solid #30405e;border-radius:10px;padding:11px 13px;font-size:14px;}
            QLineEdit:focus{border:1px solid #d7a84e;}
            QPushButton{background:#1c2941;border:1px solid #354866;border-radius:9px;padding:9px 13px;color:#e8edf7;font-weight:600;}
            QPushButton:hover{background:#263754;border-color:#d7a84e;}
            #sectionList{border:0;background:transparent;outline:0;padding:4px;}
            #sectionList::item{padding:11px 10px;margin:2px 0;border-radius:9px;color:#c6d0e2;}
            #sectionList::item:selected{background:#2b3855;color:#f6d486;font-weight:700;}
            #sectionList::item:hover{background:#19243a;}
            #sectionNo{color:#d7a84e;font-size:12px;font-weight:800;letter-spacing:1.5px;}
            #sectionTitle{font-family:'Noto Sans Gurmukhi','Nirmala UI';font-size:27px;font-weight:800;color:#f2f5fa;}
            #rule{color:#27334b;}
            #verseView,#notesView{background:#0d1423;border:0;border-radius:10px;padding:8px;font-family:'Noto Sans Gurmukhi','Nirmala UI';}
            #verseView{font-size:19px;line-height:1.7;}
            #notesView{font-size:14px;line-height:1.6;}
            #sourceCard{background:#171f33;border:1px solid #2e3b56;border-radius:10px;padding:12px;color:#9eabc1;}
            QStatusBar{background:#080c17;color:#7888a4;border-top:1px solid #202b40;}
            """)
        else:
            self.setStyleSheet("""
            QWidget{background:#f5f2ea;color:#26251f;font-family:'Noto Sans','Nirmala UI',sans-serif;}
            QToolBar{background:#fffdf8;border:0;padding:8px 10px;}
            #toolbarTitle{font-weight:800;letter-spacing:1px;color:#73551b;font-size:14px;}
            #hero{background:#fffaf0;border:1px solid #dfd0ae;border-radius:18px;}
            #heroTitle{font-family:'Noto Sans Gurmukhi','Nirmala UI';font-size:36px;font-weight:800;color:#795719;}
            #heroSub{font-size:14px;color:#756f63;}
            #panel{background:#fffdf9;border:1px solid #ded6c7;border-radius:16px;}
            #panelTitle{font-size:12px;font-weight:800;letter-spacing:1.5px;color:#817969;}
            #muted{color:#91897c;font-size:12px;}
            QLineEdit{background:#fff;border:1px solid #d6ccba;border-radius:10px;padding:11px 13px;font-size:14px;}
            QPushButton{background:#f0e9db;border:1px solid #d5c7ad;border-radius:9px;padding:9px 13px;color:#433a2c;font-weight:600;}
            #sectionList{border:0;background:transparent;outline:0;}
            #sectionList::item{padding:11px 10px;margin:2px 0;border-radius:9px;}
            #sectionList::item:selected{background:#eee1c1;color:#76551a;font-weight:700;}
            #sectionNo{color:#9b741f;font-size:12px;font-weight:800;letter-spacing:1.5px;}
            #sectionTitle{font-family:'Noto Sans Gurmukhi','Nirmala UI';font-size:27px;font-weight:800;color:#332d24;}
            #verseView,#notesView{background:#fffcf7;border:0;border-radius:10px;padding:8px;font-family:'Noto Sans Gurmukhi','Nirmala UI';}
            #verseView{font-size:19px;}
            #notesView{font-size:14px;}
            #sourceCard{background:#f4eddf;border:1px solid #dfd0ae;border-radius:10px;padding:12px;color:#716755;}
            QStatusBar{background:#eee8dc;color:#776f62;border-top:1px solid #ddd3c2;}
            """)

    def toggle_theme(self):
        self.dark = not self.dark
        self.apply_theme()

    def load_sections(self, query=""):
        self.section_list.blockSignals(True); self.section_list.clear()
        rows = self.db.sections(query)
        for r in rows:
            item = QListWidgetItem(f"{r['section_no']:>3}   {r['title']}")
            item.setData(Qt.UserRole, r['section_no'])
            self.section_list.addItem(item)
        self.section_list.blockSignals(False)
        self.count_label.setText(f"{len(rows)} sections")
        if rows: self.section_list.setCurrentRow(0)
        self.statusBar().showMessage(f"Showing {len(rows)} sections")

    def run_search(self):
        q=self.search.text().strip()
        if not q:
            self.load_sections(); return
        self.load_sections(q)
        self.statusBar().showMessage(f"Search results for: {q}")

    def section_changed(self, current, previous):
        if not current: return
        no=current.data(Qt.UserRole); self.show_section(no)

    def show_section(self, no):
        row=self.db.section(no)
        if not row: return
        self.current_no=no
        self.section_no.setText(f"SECTION {no:03d}")
        self.section_title.setText(row['title'])
        self.page_label.setText(f"Source PDF pages {row['start_page']}–{row['end_page']}")
        verses=self.db.verses(no)
        html=[]
        for v in verses:
            page = f"<span style='color:#8795ad;font-size:11px'>p. {v['source_page']}</span>" if v['source_page'] else ""
            text=v['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            html.append(f"<div style='margin-bottom:18px'><span style='color:#d7a84e;font-weight:700'>{v['verse_no']}.</span> {text}<br>{page}</div>")
        self.verses.setHtml(''.join(html) or '<i>No verse records found.</i>')
        notes=self.db.notes(no)
        nh=[]
        for n in notes:
            t=n['note_text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            nh.append(f"<p>{t}</p>")
        if not nh and row['notes']:
            nh=[f"<p>{str(row['notes']).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')}</p>"]
        self.notes.setHtml(''.join(nh) or '<p>No explanatory note recorded for this section.</p>')
        meta=self.db.metadata()
        self.source.setText(f"<b>Source</b><br>{meta.get('source','Punjabi Library')}<br>PDF: {meta.get('source_file',PDF_NAME)}<br><br><b>Extraction note</b><br>{meta.get('extraction_note','Source page retained for verification.')}" )
        self.statusBar().showMessage(f"Section {no} • {len(verses)} verse lines")

    def open_pdf(self):
        default = Path(self.db.path).parent / PDF_NAME
        path = str(default) if default.exists() else ""
        if not path:
            path,_=QFileDialog.getOpenFileName(self,"Open Heer Waris Shah PDF","","PDF files (*.pdf)")
        if path:
            try:
                import webbrowser; webbrowser.open(Path(path).resolve().as_uri())
            except Exception as e:
                QMessageBox.warning(self,"Open PDF",str(e))


def main():
    app=QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setFont(QFont("Noto Sans", 10))
    here=Path(__file__).resolve().parent
    db_path=here/DB_NAME
    if not db_path.exists():
        QMessageBox.critical(None,"Database not found",f"Place {DB_NAME} beside this application.")
        return 1
    win=Explorer(db_path); win.show()
    return app.exec()

if __name__=='__main__':
    raise SystemExit(main())
