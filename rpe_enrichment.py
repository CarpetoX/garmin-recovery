import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ACTIVITIES_PATH = Path("activities.json")
FEEDBACK_PATH = Path("training_feedback.json")
ADVANCED_PATH = Path("advanced_analytics.json")
DAILY_PATH = Path("daily_summary.json")
WEEKLY_PATH = Path("weekly_summary.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except Exception:
            return None
    return None


def valid_rpe(value):
    value = number(value)
    if value is None or not (0 <= value <= 10):
        return None
    return value


def normalize_feedback(raw):
    out = {}
    if not isinstance(raw, dict):
        return out

    rows = raw.get("activities", raw)

    if isinstance(rows, dict):
        iterable = []
        for activity_id, item in rows.items():
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("activity_id", activity_id)
                iterable.append(row)
    elif isinstance(rows, list):
        iterable = rows
    else:
        iterable = []

    for item in iterable:
        if not isinstance(item, dict):
            continue
        activity_id = (
            item.get("activity_id")
            or item.get("id")
            or item.get("ID actividad")
        )
        rpe = valid_rpe(item.get("rpe", item.get("RPE")))
        if not activity_id or rpe is None:
            continue

        out[str(activity_id)] = {
            "date": item.get("date") or item.get("Fecha"),
            "activity": item.get("activity") or item.get("Actividad"),
            "rpe": rpe,
            "registered": item.get("registered") or item.get("Registrado"),
            "sensations": item.get("sensations") or item.get("Sensaciones"),
            "notes": item.get("notes") or item.get("Notas"),
            "detail_json": (
                item.get("detail_json")
                or item.get("Detalle JSON")
                or item.get("detail")
            ),
        }

    return out


def fresh_url(url):
    """Evita respuestas CSV obsoletas de Google/Apps Script."""
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.append(("_garmin_cache_bust", str(time.time_ns())))
    return urllib.parse.urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urllib.parse.urlencode(query),
            parts.fragment,
        )
    )


def feedback_from_csv(url):
    if not url:
        return {}

    req = urllib.request.Request(
        fresh_url(url),
        headers={
            "User-Agent": "Garmin-Recovery-RPE/1.1",
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        text = response.read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    return normalize_feedback({"activities": rows})


def intervals_rpe(activity):
    if not isinstance(activity, dict):
        return None

    for key in ("session_rpe", "icu_rpe", "perceived_exertion"):
        value = valid_rpe(activity.get(key))
        if value is not None:
            return value

    return None


def main():
    local_raw = load_json(FEEDBACK_PATH, {})
    feedback = normalize_feedback(local_raw)

    remote_url = os.environ.get("RPE_CSV_URL", "").strip()
    remote_error = None
    remote_count = 0
    remote_latest_date = None

    if remote_url:
        try:
            remote = feedback_from_csv(remote_url)
            remote_count = len(remote)
            remote_latest_date = max(
                (
                    str(item.get("date"))
                    for item in remote.values()
                    if isinstance(item, dict) and item.get("date")
                ),
                default=None,
            )
            feedback.update(remote)
        except Exception as exc:
            remote_error = f"{type(exc).__name__}: {exc}"

    activities = load_json(ACTIVITIES_PATH, [])
    if not isinstance(activities, list):
        activities = []

    original_bytes = (
        ACTIVITIES_PATH.read_bytes()
        if ACTIVITIES_PATH.exists()
        else b"[]\n"
    )

    original_rpe = {}
    matched = 0
    injected = 0
    discrepancies = []

    for activity in activities:
        if not isinstance(activity, dict):
            continue

        activity_id = str(activity.get("id") or "")
        if not activity_id:
            continue

        interval_value = intervals_rpe(activity)
        original_rpe[activity_id] = interval_value

        row = feedback.get(activity_id)
        if not isinstance(row, dict):
            continue

        matched += 1
        feedback_value = valid_rpe(row.get("rpe"))
        if feedback_value is None:
            continue

        if interval_value is None:
            activity["session_rpe"] = feedback_value
            injected += 1
        elif abs(interval_value - feedback_value) >= 0.5:
            discrepancies.append(
                {
                    "activity_id": activity_id,
                    "intervals_rpe": interval_value,
                    "feedback_rpe": feedback_value,
                    "delta": round(interval_value - feedback_value, 1),
                }
            )

    snapshot = {
        "source": (
            "RPE_CSV_URL + local snapshot"
            if remote_url
            else "Google Sheet snapshot / manual feedback"
        ),
        "source_fetch_policy": "cache_bust_query + no_cache_headers",
        "spreadsheet_id": "1vbxls-yyBOs8_gAmp9ld2WI_Ss9jvXNMFbxV5TKWX_k",
        "sheet": "RPE",
        "remote_rows_loaded": remote_count,
        "remote_latest_date": remote_latest_date,
        "activities": feedback,
    }
    if remote_error:
        snapshot["remote_fetch_error"] = remote_error

    save_json(FEEDBACK_PATH, snapshot)

    try:
        save_json(ACTIVITIES_PATH, activities)

        import advanced_analytics
        advanced_analytics.main()

    finally:
        ACTIVITIES_PATH.write_bytes(original_bytes)

    advanced = load_json(ADVANCED_PATH, {})

    summary = {
        "feedback_activities": len(feedback),
        "matched_activities": matched,
        "used_as_primary_rpe": injected,
        "remote_csv_configured": bool(remote_url),
        "remote_rows_loaded": remote_count,
        "remote_latest_date": remote_latest_date,
        "remote_fetch_policy": "cache_bust_query + no_cache_headers",
        "remote_fetch_error": remote_error,
        "discrepancies": discrepancies,
        "policy": (
            "Intervals RPE has priority when present; external feedback fills "
            "missing RPE. Differences >=0.5 are reported."
        ),
    }

    if isinstance(advanced, dict):
        advanced["rpe_feedback"] = summary

        rows = advanced.get("activity_analysis") or []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                activity_id = str(row.get("activity_id") or "")
                internal = row.get("internal_load")
                if not isinstance(internal, dict):
                    continue

                fb = feedback.get(activity_id)
                fb_rpe = valid_rpe(fb.get("rpe")) if isinstance(fb, dict) else None
                int_rpe = original_rpe.get(activity_id)

                # Mantener la información del atleta separada de los ejercicios
                # detectados automáticamente por Garmin (pueden ser erróneos).
                if isinstance(fb, dict):
                    row["self_reported"] = {
                        "activity": fb.get("activity"),
                        "rpe": fb_rpe,
                        "sensations": fb.get("sensations"),
                        "notes": fb.get("notes"),
                        "detail_json": fb.get("detail_json"),
                        "source": "training_feedback",
                    }

                internal["rpe_feedback"] = fb_rpe
                internal["rpe_intervals"] = int_rpe

                if int_rpe is not None:
                    internal["rpe_source"] = "intervals"
                elif fb_rpe is not None:
                    internal["rpe_source"] = "training_feedback"
                else:
                    internal["rpe_source"] = None

                internal["rpe_discrepancy"] = (
                    round(int_rpe - fb_rpe, 1)
                    if int_rpe is not None and fb_rpe is not None
                    else None
                )

        save_json(ADVANCED_PATH, advanced)

    for path in (DAILY_PATH, WEEKLY_PATH):
        obj = load_json(path, {})
        if isinstance(obj, dict):
            block = obj.get("advanced_analytics")
            if isinstance(block, dict):
                block["rpe_feedback"] = summary
                obj["advanced_analytics"] = block
                save_json(path, obj)

    print(
        json.dumps(
            {
                "status": "success",
                "feedback_activities": len(feedback),
                "matched_activities": matched,
                "used_as_primary_rpe": injected,
                "remote_csv_configured": bool(remote_url),
                "remote_rows_loaded": remote_count,
                "remote_latest_date": remote_latest_date,
                "remote_fetch_error": remote_error,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
