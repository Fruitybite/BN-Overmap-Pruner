#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cataclysm: Bright Night map.sqlite3 pruner (overmap-safe grids edition)

What it does:
- Keep only user-specified map coords (e.g. "119.183.10") as *.map entries in table `files`.
- Delete all other `maps/%/*.map` entries.
- Keep only the overmap files `o.<omx>.<omy>` that contain the kept coords.
- IMPORTANT (NEW FIX):
  - BEFORE deleting anything, snapshot these fields from each kept overmap:
      "electric_grid_connections", "fluid_grid_connections", "fluid_grid_storage"
  - After pruning, restore those fields back into the kept overmaps verbatim.
  - With --remove-grids, wipe those fields instead (do not restore).

Why:
- In some saves, the overmap tiling for x/y is 180-based (example: 119.183.10 belongs to o.0.1 and local is 119,3,10),
  so computing overmaps using 360 (or submap logic) will be wrong and will delete the real overmap holding your grids.
- This script therefore uses `--span` as the OVERMAP coordinate span (default 180),
  matching your observed behavior.

Data model:
- `files` table contains:
  - `maps/.../<x>.<y>.<z>.map` blobs
  - `o.<omx>.<omy>` blobs (overmap JSON, usually zlib-compressed) with grid fields.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import zlib
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

COORD_RE = re.compile(r"^\s*(-?\d+)\.(-?\d+)\.(-?\d+)\s*$")
MAP_BASENAME_RE = re.compile(r"(-?\d+)\.(-?\d+)\.(-?\d+)\.map$")
OVERMAP_PATH_RE = re.compile(r"^o\.(-?\d+)\.(-?\d+)$")


# -------------------------
# Parsing helpers
# -------------------------
def parse_keep_coords(items: Iterable[str]) -> List[Tuple[int, int, int]]:
    coords: List[Tuple[int, int, int]] = []
    for raw in items:
        raw = raw.strip()
        if not raw:
            continue
        m = COORD_RE.match(raw)
        if not m:
            raise ValueError(f"좌표 형식이 올바르지 않습니다: {raw!r} (예: 119.183.10)")
        x, y, z = map(int, m.groups())
        coords.append((x, y, z))
    if not coords:
        raise ValueError("보존할 좌표가 비어 있습니다.")
    return coords


def read_keep_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        out: List[str] = []
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",") if p.strip()]
            out.extend(parts)
        return out


def floor_div(a: int, b: int) -> int:
    return a // b  # floor division (OK for negatives too)


def make_backup(db_path: str) -> str:
    bak_path = db_path + ".bak"
    if os.path.exists(bak_path):
        i = 1
        while True:
            candidate = f"{db_path}.bak{i}"
            if not os.path.exists(candidate):
                bak_path = candidate
                break
            i += 1
    shutil.copy2(db_path, bak_path)
    return bak_path


def chunked(seq: List[str], n: int):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def prompt_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("실행 여부를 입력해주세요. (예: Y / N)")


def resolve_db_path(ap: argparse.ArgumentParser, db_arg: Optional[str]) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if db_arg is None:
        candidate = os.path.join(script_dir, "map.sqlite3")
        if os.path.exists(candidate):
            db_path = os.path.abspath(candidate)
            print(f"[INFO] db 인자를 생략하여 스크립트 폴더의 DB를 자동 사용합니다: {db_path}")
            return db_path

        print("[ERROR] map.sqlite3를 찾지 못했습니다.")
        print(f"        스크립트 폴더: {script_dir}")
        print('        해결: (1) 스크립트와 같은 폴더에 "map.sqlite3"를 두거나,')
        print('              (2) 실행 시 DB 경로를 직접 지정하세요.')
        print()
        ap.print_usage()
        raise SystemExit(2)

    db_path = os.path.abspath(db_arg)
    if not os.path.exists(db_path):
        print(f"[ERROR] DB 파일이 없습니다: {db_path}")
        print("        해결: 올바른 map.sqlite3 경로를 지정해주세요.")
        print()
        ap.print_usage()
        raise SystemExit(2)

    return db_path


def parse_overmap_path(path: str) -> Tuple[int, int]:
    m = OVERMAP_PATH_RE.match(path)
    if not m:
        raise ValueError(f"Invalid overmap path: {path}")
    return int(m.group(1)), int(m.group(2))


# -------------------------
# Overmap blob encoding/decoding
# -------------------------
def decode_overmap_blob(compression: Optional[str], blob: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (version_line, json_obj).
    Expects text like "# version N\\n{...json...}"
    """
    if compression == "zlib":
        raw = zlib.decompress(blob)
    else:
        raw = blob

    text = raw.decode("utf-8")
    if "\n" not in text:
        raise ValueError("Overmap content missing newline separator")

    version_line, json_text = text.split("\n", 1)
    obj = json.loads(json_text)
    return version_line, obj


def encode_overmap_blob(compression: Optional[str], version_line: str, obj: Dict[str, Any]) -> bytes:
    """
    Serializes back to "# version N\\n<json>" and compresses if needed.
    """
    json_text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    text = version_line + "\n" + json_text
    raw = text.encode("utf-8")
    if compression == "zlib":
        return zlib.compress(raw)
    return raw


# -------------------------
# Overmap addressing (FIXED)
# -------------------------
def compute_overmap_for_coord(x: int, y: int, span: int) -> Tuple[int, int, int, int]:
    """
    Given a *global* coord (x,y), compute:
      omx, omy, local_x, local_y
    using the provided OVERMAP span.

    Example (your observation):
      span=180, (x,y)=(119,183) => (omx,omy)=(0,1), local=(119,3)
    """
    omx = floor_div(x, span)
    omy = floor_div(y, span)
    lx = x - omx * span
    ly = y - omy * span
    return omx, omy, lx, ly


# -------------------------
# Grid snapshot/restore (NEW)
# -------------------------
GRID_KEYS = ("electric_grid_connections", "fluid_grid_connections", "fluid_grid_storage")


def snapshot_overmap_grids(
    cur: sqlite3.Cursor,
    overmap_path: str,
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Returns (compression, version_line, grids_dict) for the overmap_path.
    grids_dict contains only GRID_KEYS with exact values (deep-copied).
    If overmap does not exist, returns (None, None, None).
    """
    cur.execute("SELECT compression, data FROM files WHERE path=?", (overmap_path,))
    row = cur.fetchone()
    if not row:
        return None, None, None

    comp, blob = row
    vline, obj = decode_overmap_blob(comp, blob)

    grids: Dict[str, Any] = {}
    for k in GRID_KEYS:
        grids[k] = obj.get(k, [])
        # deep copy to be safe
        grids[k] = json.loads(json.dumps(grids[k], ensure_ascii=False))

    return comp, vline, grids


def restore_overmap_grids(
    cur: sqlite3.Cursor,
    overmap_path: str,
    grids: Dict[str, Any],
    remove_grids: bool,
) -> None:
    """
    Load the overmap JSON, then either:
      - remove_grids=True: set GRID_KEYS to empty
      - else: restore GRID_KEYS exactly from grids snapshot
    Then update DB blob.
    """
    cur.execute("SELECT compression, data FROM files WHERE path=?", (overmap_path,))
    row = cur.fetchone()
    if not row:
        # if the overmap got deleted mistakenly, fail loudly
        raise RuntimeError(f"[GRID RESTORE] overmap not found after prune: {overmap_path}")

    comp, blob = row
    vline, obj = decode_overmap_blob(comp, blob)

    if remove_grids:
        obj["electric_grid_connections"] = []
        obj["fluid_grid_connections"] = []
        obj["fluid_grid_storage"] = []
    else:
        for k in GRID_KEYS:
            obj[k] = json.loads(json.dumps(grids.get(k, []), ensure_ascii=False))

    new_blob = encode_overmap_blob(comp, vline, obj)
    cur.execute("UPDATE files SET data=? WHERE path=?", (new_blob, overmap_path))


# -------------------------
# Optional verification (kept coords only)
# -------------------------
def extract_edges_between_kept_coords(
    db_path: str,
    keep_coords: Set[Tuple[int, int, int]],
    keep_overmaps: Set[str],
    span: int,
) -> Tuple[Set[Tuple[Tuple[int, int, int], Tuple[int, int, int]]], Set[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]]:
    """
    Build undirected edge sets between kept coords inferred from grid connections.
    This is a best-effort checker for "did edges among kept coords survive?"
    It uses your coordinate system: coord == global overmap-grid coordinate.
    """
    e_edges: Set[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = set()
    f_edges: Set[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = set()

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
        if cur.fetchone() is None:
            raise SystemExit(f"[VERIFY] {db_path}: 'files' 테이블이 없습니다.")

        for op in keep_overmaps:
            cur.execute("SELECT compression, data FROM files WHERE path=?", (op,))
            row = cur.fetchone()
            if not row:
                continue

            comp, blob = row
            _v, obj = decode_overmap_blob(comp, blob)
            omx, omy = parse_overmap_path(op)

            def consume(conns: Any, out_set: Set[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]):
                if not isinstance(conns, list):
                    return
                for entry in conns:
                    if not isinstance(entry, list) or len(entry) < 2:
                        continue
                    pos = entry[0]
                    if not (isinstance(pos, list) and len(pos) == 3 and all(isinstance(v, int) for v in pos)):
                        continue
                    lx, ly, lz = pos
                    ax = omx * span + lx
                    ay = omy * span + ly
                    az = lz
                    a = (ax, ay, az)
                    if a not in keep_coords:
                        continue

                    for d in entry[1:]:
                        if not (isinstance(d, list) and len(d) == 3 and all(isinstance(v, int) for v in d)):
                            continue
                        dx, dy, dz = d
                        b = (ax + dx, ay + dy, az + dz)
                        if b not in keep_coords:
                            continue
                        e = (a, b) if a < b else (b, a)
                        out_set.add(e)

            consume(obj.get("electric_grid_connections", []), e_edges)
            consume(obj.get("fluid_grid_connections", []), f_edges)

    finally:
        con.close()

    return e_edges, f_edges


def verify_against_original(
    original_db: str,
    target_db: str,
    keep_coords: Set[Tuple[int, int, int]],
    keep_overmaps: Set[str],
    span: int,
) -> int:
    orig_e, orig_f = extract_edges_between_kept_coords(original_db, keep_coords, keep_overmaps, span)
    new_e, new_f = extract_edges_between_kept_coords(target_db, keep_coords, keep_overmaps, span)

    missing_e = sorted(orig_e - new_e)
    missing_f = sorted(orig_f - new_f)

    print("\n=== VERIFY (kept coords only) ===")
    print(f"Original DB: {original_db}")
    print(f"Target DB:   {target_db}")
    print(f"Kept coords: {len(keep_coords)}")
    print(f"Electric edges: original {len(orig_e)}, target {len(new_e)}, missing {len(missing_e)}")
    print(f"Fluid edges:    original {len(orig_f)}, target {len(new_f)}, missing {len(missing_f)}")

    N = 50
    if missing_e:
        print(f"\n[Missing Electric edges] (showing up to {N})")
        for (a, b) in missing_e[:N]:
            print(f"  {a[0]}.{a[1]}.{a[2]}  <->  {b[0]}.{b[1]}.{b[2]}")
    if missing_f:
        print(f"\n[Missing Fluid edges] (showing up to {N})")
        for (a, b) in missing_f[:N]:
            print(f"  {a[0]}.{a[1]}.{a[2]}  <->  {b[0]}.{b[1]}.{b[2]}")

    if not missing_e and not missing_f:
        print("\nVERIFY: PASS ✅")
        return 0
    print("\nVERIFY: FAIL ❌")
    return 1


# -------------------------
# Main
# -------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Prune BN map.sqlite3 keeping specified coords; correct overmap mapping; snapshot+restore grids in kept overmaps."
    )

    ap.add_argument(
        "db",
        nargs="?",
        default=None,
        help="Path to map.sqlite3 (optional; if omitted, tries ./map.sqlite3 in the script folder)",
    )

    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--keep", help='Comma-separated coords, e.g. "119.183.10,119.183.9"')
    g.add_argument("--keep-file", help="Text file containing coords (one per line; # comments ok)")
    g.add_argument("--interactive", action="store_true", help="Prompt for coords interactively")

    # IMPORTANT: span is overmap coordinate span (default 180 per your observation)
    ap.add_argument("--span", type=int, default=180, help="Overmap coordinate span for x/y (default: 180)")

    ap.add_argument("--no-vacuum", action="store_true", help="Skip VACUUM at end (faster, but file stays larger)")
    ap.add_argument("--dry-run", action="store_true", help="Show plan; do not modify DB")
    ap.add_argument("--force", action="store_true", help="Skip Y/N confirmation")

    ap.add_argument(
        "--remove-grids",
        action="store_true",
        help="Remove ALL electric/fluid grid data in kept overmaps (default restores grids verbatim).",
    )

    ap.add_argument("--verify-against", default=None, help="Path to original DB to verify kept-coord edges.")
    ap.add_argument("--verify-only", action="store_true", help="Do not prune; only run verification.")
    args = ap.parse_args()

    db_path = resolve_db_path(ap, args.db)

    # Read keep coords
    if args.interactive:
        print("보존할 좌표를 입력하세요. 예) 119.183.10, 119.183.9")
        raw = input("> ").strip()
        keep_items = [p.strip() for p in raw.split(",") if p.strip()]
    elif args.keep_file:
        keep_items = read_keep_file(args.keep_file)
    else:
        keep_items = [p.strip() for p in args.keep.split(",") if p.strip()]

    keep_list = parse_keep_coords(keep_items)
    keep_set: Set[Tuple[int, int, int]] = set(keep_list)
    keep_basenames: Set[str] = {f"{x}.{y}.{z}.map" for (x, y, z) in keep_list}

    # Compute correct overmaps using span
    keep_overmaps: Set[str] = set()
    computed: List[Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]] = []
    for (x, y, z) in keep_list:
        omx, omy, lx, ly = compute_overmap_for_coord(x, y, args.span)
        keep_overmaps.add(f"o.{omx}.{omy}")
        computed.append(((x, y, z), (omx, omy, lx, ly)))

    print("\n=== INPUT SUMMARY ===")
    print("Keep coords:")
    for (x, y, z) in sorted(keep_list):
        print(f"  {x}.{y}.{z}")
    print("\nKeep overmaps (computed; with local x,y):")
    for ((x, y, z), (omx, omy, lx, ly)) in computed:
        print(f"  {x}.{y}.{z} -> o.{omx}.{omy}  (local {lx}.{ly}.{z})")
    print(f"\nGrid handling: {'REMOVE ALL (no restore)' if args.remove_grids else 'SNAPSHOT+RESTORE (default)'}")
    print("=====================\n")

    # Verify-only mode
    if args.verify_only:
        if not args.verify_against:
            raise SystemExit("[ERROR] --verify-only를 쓰려면 --verify-against ORIGINAL_DB가 필요합니다.")
        code = verify_against_original(
            original_db=os.path.abspath(args.verify_against),
            target_db=db_path,
            keep_coords=keep_set,
            keep_overmaps=keep_overmaps,
            span=args.span,
        )
        raise SystemExit(code)

    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys=OFF;")
        cur = con.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
        if cur.fetchone() is None:
            raise SystemExit("이 DB에는 'files' 테이블이 없습니다. (BN map.sqlite3 형식이 아닌 듯합니다)")

        # Plan deletions
        cur.execute("SELECT path FROM files WHERE path LIKE 'maps/%' AND path LIKE '%.map'")
        map_paths = [r[0] for r in cur.fetchall()]

        delete_map_paths: List[str] = []
        kept_map_paths: List[str] = []
        for p in map_paths:
            bn = os.path.basename(p)
            if bn in keep_basenames:
                kept_map_paths.append(p)
            else:
                if MAP_BASENAME_RE.search(bn):
                    delete_map_paths.append(p)

        cur.execute("SELECT path FROM files WHERE path LIKE 'o.%'")
        o_paths = [r[0] for r in cur.fetchall()]
        delete_o_paths = [p for p in o_paths if p not in keep_overmaps]
        kept_o_paths = [p for p in o_paths if p in keep_overmaps]

        print("=== PLAN ===")
        print(f"DB: {db_path}")
        print(f"Total map entries: {len(map_paths)}")
        print(f"  Will keep:        {len(kept_map_paths)}")
        print(f"  Will delete:      {len(delete_map_paths)}")
        print(f"Total overmap entries: {len(o_paths)}")
        print(f"  Will keep:            {len(kept_o_paths)}")
        print(f"  Will delete:          {len(delete_o_paths)}")
        print("===========\n")

        # Snapshot grids from kept overmaps (BEFORE any changes)
        grid_snapshots: Dict[str, Dict[str, Any]] = {}
        missing_kept_overmaps: List[str] = []

        if not args.remove_grids:
            print("[STEP] Snapshot grids from kept overmaps...")
            for op in sorted(keep_overmaps):
                comp, vline, grids = snapshot_overmap_grids(cur, op)
                if grids is None:
                    missing_kept_overmaps.append(op)
                else:
                    grid_snapshots[op] = grids

            if missing_kept_overmaps:
                print("⚠️ 경고: 아래 오버맵 파일이 DB에 없어 그리드 스냅샷을 못했습니다:")
                for op in missing_kept_overmaps:
                    print("  ", op)
                print("   (keep 좌표 계산(span)이 여전히 틀렸거나, 해당 오버맵이 DB에 없을 수 있습니다)\n")
        else:
            print("[STEP] --remove-grids: grids will be wiped in kept overmaps (no snapshot).\n")

        if args.dry_run:
            print("[DRY RUN] DB는 수정하지 않습니다.")
            return

        if not args.force:
            ok = prompt_yes_no("위 계획대로 삭제/수정할까요? (Y/N): ")
            if not ok:
                print("취소했습니다. DB는 변경되지 않았습니다.")
                return

        bak = make_backup(db_path)
        print(f"백업 생성: {bak}")

        con.execute("BEGIN;")
        try:
            # 1) Delete maps not kept
            for ch in chunked(delete_map_paths, 800):
                placeholders = ",".join(["?"] * len(ch))
                cur.execute(f"DELETE FROM files WHERE path IN ({placeholders})", ch)

            # 2) Delete overmaps not kept
            for ch in chunked(delete_o_paths, 800):
                placeholders = ",".join(["?"] * len(ch))
                cur.execute(f"DELETE FROM files WHERE path IN ({placeholders})", ch)

            # 3) Restore (or wipe) grids in kept overmaps AFTER deletion
            print("[STEP] Restore/wipe grids in kept overmaps...")
            for op in sorted(keep_overmaps):
                grids = grid_snapshots.get(op, {"electric_grid_connections": [], "fluid_grid_connections": [], "fluid_grid_storage": []})
                restore_overmap_grids(cur, op, grids, remove_grids=args.remove_grids)

            con.execute("COMMIT;")
        except Exception:
            con.execute("ROLLBACK;")
            raise

        if not args.no_vacuum:
            print("VACUUM 실행 중...")
            con.execute("VACUUM;")

        remaining_maps = con.execute("SELECT COUNT(*) FROM files WHERE path LIKE 'maps/%' AND path LIKE '%.map'").fetchone()[0]
        remaining_o = con.execute("SELECT COUNT(*) FROM files WHERE path LIKE 'o.%'").fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]

        print("\n=== DONE ===")
        print(f"Remaining map entries:     {remaining_maps}")
        print(f"Remaining overmap entries: {remaining_o}")
        print(f"Total remaining entries:   {total}")
        print(f"Modified DB: {db_path}")
        print("============")

    finally:
        con.close()

    # Optional verification after prune
    if args.verify_against:
        verify_against_original(
            original_db=os.path.abspath(args.verify_against),
            target_db=db_path,
            keep_coords=keep_set,
            keep_overmaps=keep_overmaps,
            span=args.span,
        )


if __name__ == "__main__":
    main()