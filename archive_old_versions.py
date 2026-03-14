#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
버전 정리 스크립트: 각 디렉토리에서 최신 3개 버전만 유지하고 나머지를 old/로 이동.

Usage:
    uv run archive_old_versions.py --dry-run   # 미리보기
    uv run archive_old_versions.py              # 실제 이동
"""

import argparse
import re
import shutil
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent

# 대상 디렉토리 설정: (탐색 경로, old 경로, 대상 타입)
TARGETS = [
    # 폴더 버전
    ("01.ontology", "01.ontology/old", "dir"),
    ("02.knowledge_graph", "02.knowledge_graph/old", "dir"),
    ("03.graphrag/separate", "03.graphrag/separate/old", "dir"),
    ("llm_reviews/01.ontology", "llm_reviews/01.ontology/old", "dir"),
    ("llm_reviews/02.knowledge_graph", "llm_reviews/02.knowledge_graph/old", "dir"),
    ("llm_reviews/03.graphrag/separate", "llm_reviews/03.graphrag/separate/old", "dir"),
    # 파일 버전 (llm_reviews 루트의 v*.md 파일들)
    ("llm_reviews", "llm_reviews/old", "file"),
]

VERSION_DIR_PATTERN = re.compile(r"^v(\d+)$")
VERSION_FILE_PATTERN = re.compile(r"^v(\d+)\.md$")
VERSION_RELATED_FILE_PATTERN = re.compile(r"^v(\d+)[\w_]*\.md$")

KEEP_COUNT = 3


def find_versioned_items(base_path: Path, item_type: str) -> dict[int, list[Path]]:
    """버전 번호별 항목(폴더 또는 파일) 수집."""
    versions: dict[int, list[Path]] = {}

    if not base_path.exists():
        return versions

    for item in base_path.iterdir():
        if item_type == "dir" and item.is_dir():
            m = VERSION_DIR_PATTERN.match(item.name)
            if m:
                ver = int(m.group(1))
                versions.setdefault(ver, []).append(item)

        elif item_type == "file" and item.is_file():
            m = VERSION_RELATED_FILE_PATTERN.match(item.name)
            if m:
                ver = int(m.group(1))
                versions.setdefault(ver, []).append(item)

    return versions


def archive_versions(dry_run: bool = True) -> None:
    """최신 KEEP_COUNT개 버전을 제외한 나머지를 old/로 이동."""
    total_moves = 0

    for search_rel, old_rel, item_type in TARGETS:
        base_path = ROOT / search_rel
        old_path = ROOT / old_rel

        versions = find_versioned_items(base_path, item_type)
        if not versions:
            continue

        sorted_vers = sorted(versions.keys(), reverse=True)
        keep_vers = set(sorted_vers[:KEEP_COUNT])
        archive_vers = sorted_vers[KEEP_COUNT:]

        if not archive_vers:
            continue

        print(f"\n📁 {search_rel}/ (유지: {sorted(keep_vers, reverse=True)})")

        for ver in archive_vers:
            for item in versions[ver]:
                dest = old_path / item.name
                action = "이동 예정" if dry_run else "이동 완료"

                if dry_run:
                    print(f"  {action}: {item.relative_to(ROOT)} → {dest.relative_to(ROOT)}")
                else:
                    old_path.mkdir(parents=True, exist_ok=True)
                    if dest.exists():
                        print(f"  ⚠️  건너뜀 (이미 존재): {dest.relative_to(ROOT)}")
                        continue
                    shutil.move(str(item), str(dest))
                    print(f"  {action}: {item.relative_to(ROOT)} → {dest.relative_to(ROOT)}")

                total_moves += 1

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}총 {total_moves}건 {'이동 예정' if dry_run else '이동 완료'}")


def main():
    parser = argparse.ArgumentParser(description="오래된 버전을 old/ 디렉토리로 아카이브")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 이동 없이 미리보기만 수행",
    )
    args = parser.parse_args()
    archive_versions(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
