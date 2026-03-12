#!/usr/bin/env python3
"""Divide filtrados por keyword en ventanas de fecha/hora.

Lee archivos "<Clasificacion> - filtrado.csv" y cruza por RECLAMO ID con
"<Clasificacion> - original.csv" para recuperar FECHA DE CREACION.
Luego genera CSVs por keyword y por ventana horaria.
"""

import csv
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


KEYWORDS = [
    "FALLA MASIVA",
    "PROBLEMA RESUELTO",
    "ENVIAR VT",
    "SIN FALLA",
]


@dataclass
class TimeWindow:
    label: str
    start: datetime
    end: datetime


def normalize_text(value: str) -> str:
    text = (value or "").strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(raw: str, fallback: datetime) -> datetime:
    raw = (raw or "").strip()
    if not raw:
        return fallback

    for fmt in ["%d/%m/%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    raise ValueError(f"Fecha invalida: '{raw}' (usar DD/MM/YYYY o YYYY-MM-DD)")


def parse_time(raw: str, default: str) -> str:
    raw = (raw or "").strip() or default
    if not re.match(r"^\d{2}:\d{2}$", raw):
        raise ValueError(f"Hora invalida: '{raw}' (usar HH:MM)")
    return raw


def parse_creation_datetime(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None

    for fmt in ["%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"]:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def build_windows() -> list[TimeWindow]:
    now = datetime.now()
    base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    prev_date = base_date - timedelta(days=1)

    # Defaults requeridos:
    # - Ventana 1: dia anterior 15:30 -> dia actual 08:30
    # - Ventana 2: dia actual 08:30 -> dia actual 15:30
    w1_start_date = parse_date(os.getenv("RAS_WINDOW1_START_DATE", ""), prev_date)
    w1_end_date = parse_date(os.getenv("RAS_WINDOW1_END_DATE", ""), base_date)
    w1_start = parse_time(os.getenv("RAS_WINDOW1_START", "15:30"), "15:30")
    w1_end = parse_time(os.getenv("RAS_WINDOW1_END", "08:30"), "08:30")

    w2_start_date = parse_date(os.getenv("RAS_WINDOW2_START_DATE", ""), base_date)
    w2_end_date = parse_date(os.getenv("RAS_WINDOW2_END_DATE", ""), base_date)
    w2_start = parse_time(os.getenv("RAS_WINDOW2_START", "08:30"), "08:30")
    w2_end = parse_time(os.getenv("RAS_WINDOW2_END", "15:30"), "15:30")

    w1_start_dt = datetime.strptime(f"{w1_start_date.strftime('%Y-%m-%d')} {w1_start}", "%Y-%m-%d %H:%M")
    w1_end_dt = datetime.strptime(f"{w1_end_date.strftime('%Y-%m-%d')} {w1_end}", "%Y-%m-%d %H:%M")
    w2_start_dt = datetime.strptime(f"{w2_start_date.strftime('%Y-%m-%d')} {w2_start}", "%Y-%m-%d %H:%M")
    w2_end_dt = datetime.strptime(f"{w2_end_date.strftime('%Y-%m-%d')} {w2_end}", "%Y-%m-%d %H:%M")

    if w1_start_dt > w1_end_dt:
        raise ValueError("Window1 invalida: inicio > fin")
    if w2_start_dt > w2_end_dt:
        raise ValueError("Window2 invalida: inicio > fin")

    return [
        TimeWindow("window1", w1_start_dt, w1_end_dt),
        TimeWindow("window2", w2_start_dt, w2_end_dt),
    ]


def filter_windows_by_env(windows: list[TimeWindow]) -> list[TimeWindow]:
    """Permite ejecutar solo window1 o window2 via RAS_SPLIT_ONLY_WINDOW."""
    raw = (os.getenv("RAS_SPLIT_ONLY_WINDOW", "all") or "all").strip().lower()
    if raw in {"", "all", "both", "todas"}:
        return windows

    allowed = {"window1", "window2"}
    selected = [w for w in windows if w.label.lower() == raw]
    if selected:
        return selected

    raise ValueError(
        "RAS_SPLIT_ONLY_WINDOW invalido. Usar: all, window1 o window2"
    )


def read_original_index(original_csv: Path, time_field: str) -> dict[str, str]:
    index: dict[str, str] = {}
    with original_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return index

        # Normaliza headers para tolerar variantes.
        header_map = {normalize_text(h): h for h in reader.fieldnames if h}
        id_col = header_map.get("RECLAMO ID")
        if time_field == "comment":
            date_col = header_map.get("ULTIMA FECHA COMENTARIO")
        else:
            date_col = header_map.get("FECHA DE CREACION")
        if not id_col or not date_col:
            return index

        for row in reader:
            rid = (row.get(id_col) or "").strip()
            dt = (row.get(date_col) or "").strip()
            if rid and dt and rid not in index:
                index[rid] = dt
    return index


def safe_name(text: str) -> str:
    base = re.sub(r"[\\/:*?\"<>|]", " ", text)
    base = re.sub(r"\s+", " ", base).strip()
    return base


def main() -> None:
    download_dir = Path(os.getenv("TELECENTRO_DOWNLOAD_DIR", "downloads").strip() or "downloads")
    output_dir = Path(os.getenv("RAS_SPLIT_OUTPUT_DIR", str(download_dir / "divididos")).strip())
    output_dir.mkdir(parents=True, exist_ok=True)

    windows = filter_windows_by_env(build_windows())
    time_field = (os.getenv("RAS_SPLIT_TIME_FIELD", "comment") or "comment").strip().lower()
    if time_field not in {"comment", "creation"}:
        raise ValueError("RAS_SPLIT_TIME_FIELD invalido. Usar: comment o creation")

    print(f"Campo temporal para ventanas: {time_field}")
    for w in windows:
        print(
            f"Ventana {w.label}: {w.start.strftime('%d/%m/%Y %H:%M')} -> "
            f"{w.end.strftime('%d/%m/%Y %H:%M')}"
        )

    filtered_files = sorted(download_dir.glob("* - filtrado.csv"))
    if not filtered_files:
        print(f"No se encontraron filtrados en {download_dir}")
        return

    buckets: dict[tuple[str, str], list[list[str]]] = {}

    for filtered in filtered_files:
        classification = filtered.name.replace(" - filtrado.csv", "")
        original = download_dir / f"{classification} - original.csv"
        if not original.exists():
            print(f"Aviso: falta original para '{classification}': {original}")
            continue

        date_by_reclamo = read_original_index(original, time_field)
        with filtered.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rid = (row.get("RECLAMO ID") or "").strip()
                cliente = (row.get("CLIENTE NUMERO") or "").strip()
                motivo = normalize_text((row.get("Motivo") or "").strip())
                if not rid or not motivo:
                    continue
                if motivo not in KEYWORDS:
                    continue

                created_raw = date_by_reclamo.get(rid, "")
                created_dt = parse_creation_datetime(created_raw)
                if not created_dt:
                    continue

                for w in windows:
                    if w.start <= created_dt <= w.end:
                        key = (w.label, motivo)
                        buckets.setdefault(key, []).append(
                            [
                                rid,
                                cliente,
                                motivo,
                                created_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            ]
                        )

    for w in windows:
        for keyword in KEYWORDS:
            key = (w.label, keyword)
            rows = buckets.get(key, [])
            out_name = f"{safe_name(w.label)} - {safe_name(keyword)}.csv"
            out_path = output_dir / out_name
            with out_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "RECLAMO ID",
                    "CLIENTE NUMERO",
                    "Motivo",
                    "FECHA REFERENCIA",
                ])
                writer.writerows(rows)
            print(f"Generado: {out_path} (filas={len(rows)})")


if __name__ == "__main__":
    main()
