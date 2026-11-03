"""Generuje docs/SYSTEM.docx z dokumentacji systemu."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


def set_run_font(run, size=11, bold=False):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    run.font.size = Pt(size)
    run.bold = bold


def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        set_run_font(run, size=16 - level, bold=True)
    return h


def add_para(doc, text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, bold=bold)
    p.paragraph_format.space_after = Pt(6)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(item)
        set_run_font(run)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for run in p.runs:
                set_run_font(run, bold=True, size=10)
    for r_i, row in enumerate(rows):
        cells = table.rows[r_i + 1].cells
        for c_i, val in enumerate(row):
            cells[c_i].text = str(val)
            for p in cells[c_i].paragraphs:
                for run in p.runs:
                    set_run_font(run, size=10)
    doc.add_paragraph()


def main():
    out = Path(__file__).resolve().parent / "SYSTEM.docx"
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("Analiza dynamiki pisania komputerowego")
    set_run_font(r, size=18, bold=True)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = subtitle.add_run("Dokumentacja systemu (keystroke dynamics)")
    set_run_font(r, size=14)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta.add_run(
        "Domena: https://pismo.iit.sggw.pl\n"
        "Repozytorium: https://github.com/klipka78/analiza-dynamiki-pisania"
    )
    set_run_font(r, size=10)

    add_heading(doc, "1. Cel systemu", 1)
    add_para(
        doc,
        "System zbiera dynamikę wprowadzania tekstu z klawiatury (keystroke dynamics), "
        "a nie wygląd liter. Na podstawie mikroczasów naciskania i zwalniania klawiszy, "
        "odstępów między znakami oraz wzorców poprawek bada się, czy da się rozpoznać "
        "autora (uczestnika) wprowadzanego tekstu.",
    )
    add_para(doc, "Typowy przebieg badania:", bold=True)
    add_bullets(
        doc,
        [
            "Uczestnik dostaje identyfikator (np. P017).",
            "Przepisuje jeden z tekstów kontrolnych (A / B / C) naturalnym tempem.",
            "Przeglądarka rejestruje każde keydown / keyup z czasem względnym.",
            "Sesja trafia do bazy; badacz eksportuje CSV i buduje model rozpoznawania.",
        ],
    )
    add_para(
        doc,
        "Dodatkowo w repozytorium jest wariant offline: makro Microsoft Word (folder word-macro/) "
        "z tym samym pomysłem pomiaru.",
    )

    add_heading(doc, "2. Funkcje systemu", 1)
    add_table(
        doc,
        ["Obszar", "Funkcja"],
        [
            ["Sesja uczestnika (/)", "Start/Stop rejestracji, teksty A/B/C, wysłanie sesji"],
            ["Panel badacza (/admin)", "Lista sesji, eksport CSV, token ADMIN_TOKEN"],
            ["API", "Zapis sesji, health, zadania, eksport"],
            ["Makro Word", "Rejestracja w UserForm + lokalny CSV"],
        ],
    )
    add_para(
        doc,
        "Uwaga: nie jest to keylogger ogólnego użytku — rejestracja działa tylko w polu "
        "zadania, na tekstach kontrolnych, za zgodą uczestnika badania.",
    )

    add_heading(doc, "3. Architektura i technologie", 1)
    add_para(
        doc,
        "Uczestnik → HTTPS → reverse proxy → Apache (:80, ProxyPass) → "
        "kontener Docker nginx/web (:8080) → SPA oraz proxy /api → kontener FastAPI (:8000) → "
        "SQLite w wolumenie Dockera.",
    )
    add_table(
        doc,
        ["Warstwa", "Technologia", "Rola"],
        [
            ["Frontend", "React 18, TypeScript, Vite", "UI sesji i panelu"],
            ["Serwowanie SPA", "nginx (kontener web)", "Pliki statyczne + proxy /api"],
            ["Backend", "FastAPI, Uvicorn, Pydantic, SQLAlchemy 2", "API REST, walidacja, ORM"],
            ["Baza", "SQLite (wolumen Docker)", "Sesje + zdarzenia klawiszy"],
            ["Orkiestracja", "Docker Compose", "Usługi api + web"],
            ["Edge", "Apache 2 + ProxyPass", "Domena pismo.iit.sggw.pl → :8080"],
            ["Offline", "VBA / Word UserForm", "Alternatywne zbieranie CSV"],
        ],
    )

    add_heading(doc, "4. Składowanie danych", 1)
    add_heading(doc, "4.1. Lokalizacja (Docker)", 2)
    add_table(
        doc,
        ["Element", "Wartość"],
        [
            ["Zmienna", "DATABASE_URL=sqlite:////data/keystroke.db"],
            ["Ścieżka w kontenerze api", "/data/keystroke.db"],
            ["Wolumen Compose", "pismo_keystroke_data"],
            [
                "Host (typowo)",
                "/var/lib/docker/volumes/pismo_keystroke_data/_data/keystroke.db",
            ],
        ],
    )
    add_para(
        doc,
        "Eksport: panel /admin lub GET /api/sessions/{uid}/export.csv oraz "
        "GET /api/export/all.csv (nagłówek X-Admin-Token).",
    )

    add_heading(doc, "4.2. Model danych", 2)
    add_para(doc, "Tabela sessions — jedna próba przepisania tekstu:", bold=True)
    add_bullets(
        doc,
        [
            "session_uid, participant_id, task_id (A/B/C)",
            "reference_text, typed_text",
            "user_agent, language, event_count, created_at",
        ],
    )
    add_para(doc, "Tabela events — pojedyncze zdarzenia klawiszy:", bold=True)
    add_bullets(
        doc,
        [
            "seq, elapsed_ms (od Start), event_type (down/up)",
            "code, key, key_code, shift, ctrl, alt",
        ],
    )

    add_heading(doc, "4.3. Format CSV", 2)
    add_para(
        doc,
        "Kolumny: seq, elapsed_ms, event_type, code, key, key_code, shift, ctrl, alt. "
        "Etykieta autora = participant_id w sesji.",
    )

    add_heading(doc, "5. SQLite a PostgreSQL", 1)
    add_para(
        doc,
        "Na etapie pracy dyplomowej / pilotażu SQLite wystarczy. PostgreSQL warto rozważyć "
        "przy równoległym dużym ruchu lub milionach zdarzeń i potrzebie stałego BI.",
    )
    add_table(
        doc,
        ["Kryterium", "SQLite (obecnie)", "PostgreSQL"],
        [
            ["Skala badania (dziesiątki–setki sesji)", "OK", "OK"],
            ["Równoległe zapisy", "Ograniczone", "Lepsze"],
            ["Backup", "Kopia pliku / wolumenu", "pg_dump"],
            ["Utrzymanie", "Minimalne", "Większe (kontener, hasła)"],
        ],
    )

    add_heading(doc, "6. Analiza danych i rozpoznawanie użytkownika", 1)
    add_heading(doc, "6.1. Protokół zbierania", 2)
    add_table(
        doc,
        ["Parametr", "Sugestia"],
        [
            ["Liczba osób", "≥ 10–20"],
            ["Sesje na osobę", "≥ 5–10 (różne dni / warunki)"],
            ["Teksty", "A, B, C — te same dla wszystkich"],
            ["Etykieta", "Stałe participant_id (P001, P002…)"],
            ["Instrukcja", "Naturalne tempo, poprawki dozwolone"],
        ],
    )

    add_heading(doc, "6.2. Cechy (feature engineering)", 2)
    add_bullets(
        doc,
        [
            "Hold time (dwell) — czas przytrzymania: up.t − down.t (per code).",
            "Flight time / digraph latency — odstęp między kolejnymi naciśnięciami.",
            "Trigraph — latencje dla trójek znaków (opcjonalnie).",
            "Tempo — znaki/min (WPM) na sesję.",
            "Poprawki — udział Backspace / Delete.",
            "Statystyki: średnia, mediana, odchylenie, percentyle; wektor stałej długości na sesję.",
        ],
    )

    add_heading(doc, "6.3. Modele", 2)
    add_table(
        doc,
        ["Poziom", "Metoda", "Uwagi"],
        [
            ["Baseline", "k-NN / odległość Manhattan", "Klasyczny w literaturze KD"],
            ["Klasyczny ML", "Random Forest, SVM (RBF)", "Dobry start do pracy"],
            ["Zaawansowane", "LSTM / Transformer na sekwencji", "Więcej danych"],
        ],
    )
    add_para(
        doc,
        "Scenariusze: identyfikacja 1:N („który uczestnik?”) oraz weryfikacja 1:1 "
        "(„czy to nadal P017?”). Metryki: accuracy, balanced accuracy, macierz pomyłek, EER.",
    )

    add_heading(doc, "6.4. Pipeline analizy (offline)", 2)
    add_bullets(
        doc,
        [
            "Eksport CSV z panelu admina.",
            "pandas: sesje + eventy → hold / digraph → macierz cech X, etykiety y.",
            "Podział train/test po session_uid.",
            "scikit-learn (np. Random Forest) → raport accuracy i confusion matrix.",
        ],
    )
    add_para(
        doc,
        "Narzędzia: Python, pandas, scikit-learn, matplotlib/seaborn; opcjonalnie Jupyter "
        "na stacji badacza (nie musi działać na serwerze WWW).",
    )

    add_heading(doc, "6.5. Ograniczenia", 2)
    add_bullets(
        doc,
        [
            "Inna klawiatura / laptop vs zewnętrzna.",
            "Układ PL vs EN, zmęczenie, pośpiech.",
            "Mała liczba sesji → ryzyko przeuczenia.",
            "Wyniki dla tekstów kontrolnych nie przenoszą się automatycznie na tekst swobodny.",
        ],
    )

    add_heading(doc, "7. Endpointy API", 1)
    add_table(
        doc,
        ["Metoda", "Ścieżka", "Auth", "Opis"],
        [
            ["GET", "/api/health", "—", "Status"],
            ["GET", "/api/tasks", "—", "Teksty A/B/C"],
            ["POST", "/api/sessions", "—", "Zapis sesji + eventów"],
            ["GET", "/api/sessions", "X-Admin-Token", "Lista"],
            ["GET", "/api/sessions/{uid}/export.csv", "token", "CSV sesji"],
            ["GET", "/api/export/all.csv", "token", "Wszystkie eventy"],
        ],
    )

    add_heading(doc, "8. Operacje na produkcji", 1)
    add_bullets(
        doc,
        [
            "Status: docker compose ps; curl http://127.0.0.1:8080/api/health",
            "Po zmianie .env (np. ADMIN_TOKEN): docker compose up -d --force-recreate",
            "Aktualizacja: git pull && docker compose up -d --build",
            "Backup: kopia pliku keystroke.db z wolumenu pismo_keystroke_data",
        ],
    )

    add_heading(doc, "9. Bezpieczeństwo i etyka", 1)
    add_bullets(
        doc,
        [
            "Rejestracja tylko w kontrolowanym zadaniu — nie treści haseł z innych stron.",
            "participant_id powinien być anonimowy (kod, nie nazwisko).",
            "ADMIN_TOKEN wyłącznie w .env (nie w git).",
            "Kontener nasłuchuje na 127.0.0.1:8080; API admina wymaga tokenu.",
            "Uczestników informować o celu badania i zakresie danych (RODO / zgoda).",
        ],
    )

    add_heading(doc, "10. Podsumowanie", 1)
    add_table(
        doc,
        ["Pytanie", "Odpowiedź"],
        [
            ["Gdzie dane?", "SQLite w wolumenie Docker pismo_keystroke_data"],
            ["Postgres już teraz?", "Nie wymagany; SQLite OK do zbierania i ML offline"],
            [
                "Jak rozpoznać użytkownika?",
                "Wiele sesji na ID → cechy hold/digraph → klasyfikator (RF/SVM/k-NN)",
            ],
            ["Skąd dane do ML?", "Panel /admin → eksport CSV"],
        ],
    )

    footer = doc.add_paragraph()
    r = footer.add_run(
        "Dokument wygenerowany automatycznie na podstawie docs/SYSTEM.md w repozytorium projektu."
    )
    set_run_font(r, size=9)

    doc.save(out)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
