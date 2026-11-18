"""Расчёт Cohen's kappa для согласованности экспертов (Глава 3-4 ВКР).

Оценки: экспертная шкала Ликерта 1-5 (ТЗ п.7.3). Цель: kappa >= 0.6.

Формат входного файла (CSV или JSONL), поля:
  scenario_id, expert_1, expert_2[, expert_3]

Использование:
  python -m eval.cohen_kappa --file expert_scores.csv
  python -m eval.cohen_kappa --file expert_scores.csv --e1 expert_1 --e2 expert_2

Без файла — демонстрационный расчёт.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

# Шкала интерпретации Landis & Koch
KAPPA_INTERPRETATION = [
    (0.81, "почти полное согласие"),
    (0.61, "существенное согласие (цель достигнута)"),
    (0.41, "умеренное согласие"),
    (0.21, "слабое согласие"),
    (0.00, "ничтожное согласие"),
]


def interpret(k: float) -> str:
    for threshold, label in KAPPA_INTERPRETATION:
        if k >= threshold:
            return label
    return "отрицательное согласие"


def kappa(expert_a: list[int], expert_b: list[int]) -> float:
    """Cohen's kappa для двух экспертов."""
    if len(expert_a) != len(expert_b):
        raise ValueError("Длины оценок экспертов не совпадают")
    if not expert_a:
        raise ValueError("Пустые оценки")
    return float(cohen_kappa_score(expert_a, expert_b))


def load_scores(path: Path) -> tuple[dict[str, list[int]], list[str]]:
    """Загрузить оценки из CSV или JSONL.

    Returns: (scores_by_expert, scenario_ids)
    """
    scores: dict[str, list[int]] = {}
    ids: list[str] = []

    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.append(row["scenario_id"])
                for key, val in row.items():
                    if key == "scenario_id" or val == "":
                        continue
                    scores.setdefault(key, []).append(int(val))
    else:  # JSONL
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                ids.append(obj["scenario_id"])
                for key, val in obj.items():
                    if key == "scenario_id" or val in (None, ""):
                        continue
                    scores.setdefault(key, []).append(int(val))

    return scores, ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Cohen's kappa для экспертных оценок")
    parser.add_argument("--file", type=Path, help="CSV/JSONL с оценками экспертов")
    parser.add_argument("--e1", default=None, help="Имя первого эксперта (колонка)")
    parser.add_argument("--e2", default=None, help="Имя второго эксперта (колонка)")
    args = parser.parse_args()

    if args.file and args.file.exists():
        scores, ids = load_scores(args.file)
        experts = list(scores.keys())
        print(f"Загружено сценариев: {len(ids)}, экспертов: {len(experts)} ({', '.join(experts)})")

        e1 = args.e1 or experts[0]
        e2 = args.e2 or experts[1] if len(experts) > 1 else None
        if e2 is None:
            print("Нужно минимум 2 эксперта")
            return
        k = kappa(scores[e1], scores[e2])
        print(f"kappa({e1}, {e2}) = {k:.3f} — {interpret(k)}")
        print(f"Цель kappa >= 0.6: {'ДОСТИГНУТА' if k >= 0.6 else 'НЕ достигнута'}")

        # Все пары экспертов, если их >2
        for i in range(len(experts)):
            for j in range(i + 1, len(experts)):
                a, b = experts[i], experts[j]
                if {a, b} == {e1, e2}:
                    continue
                kk = kappa(scores[a], scores[b])
                print(f"kappa({a}, {b}) = {kk:.3f} — {interpret(kk)}")
    else:
        # Демонстрация
        a = [5, 4, 3, 5, 4, 3, 5]
        b = [4, 4, 3, 5, 3, 3, 5]
        k = kappa(a, b)
        print(f"Демо: Cohen's kappa = {k:.3f} — {interpret(k)}")


if __name__ == "__main__":
    main()
