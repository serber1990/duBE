import json
import os

import pytest

import duBE
from duBE import human_size, parse_size, scan, select_entries


def lsize(path):
    return os.lstat(path).st_size


@pytest.fixture
def tree(tmp_path):
    """
    root/
      a/
        b/big.bin      200000 bytes
        small.bin        5000 bytes
      c/
        hard.bin       hard link to a/b/big.bin
        empty
    """
    root = tmp_path / "root"
    (root / "a" / "b").mkdir(parents=True)
    (root / "c").mkdir()
    (root / "a" / "b" / "big.bin").write_bytes(b"x" * 200_000)
    (root / "a" / "small.bin").write_bytes(b"y" * 5_000)
    os.link(root / "a" / "b" / "big.bin", root / "c" / "hard.bin")
    (root / "c" / "empty").touch()
    return root


def test_sizes_are_cumulative(tree):
    res = scan(str(tree), apparent_size=True, excludes=())
    a, b = str(tree / "a"), str(tree / "a" / "b")
    assert res.dirs[b] == lsize(b) + 200_000
    assert res.dirs[a] == lsize(a) + res.dirs[b] + 5_000
    assert res.total == res.dirs[str(tree)]


def test_hard_links_counted_once(tree):
    res = scan(str(tree), apparent_size=True, excludes=())
    dirs = [tree, tree / "a", tree / "a" / "b", tree / "c"]
    assert res.total == sum(lsize(d) for d in dirs) + 200_000 + 5_000


def test_disk_usage_matches_blocks(tree):
    res = scan(str(tree), excludes=())
    assert res.total >= 200_000  # counted in 512-byte blocks, at least the data


def test_trailing_slash_is_normalised(tree):
    res = scan(str(tree) + "/", excludes=())
    assert res.root == str(tree)
    assert str(tree / "a") in res.dirs


def test_symlinks_skipped_by_default_and_loops_detected(tree):
    os.symlink("..", tree / "a" / "loop")
    plain = scan(str(tree), apparent_size=True, excludes=())
    followed = scan(str(tree), apparent_size=True, follow_symlinks=True, excludes=())
    assert plain.total == followed.total  # the loop points back into the tree: nothing new


def test_excludes_by_name_and_path(tree):
    res = scan(str(tree), apparent_size=True, excludes=["b", str(tree / "c")])
    assert str(tree / "a" / "b") not in res.dirs
    assert str(tree / "c") not in res.dirs
    res = scan(str(tree), apparent_size=True, excludes=["*.bin"], include_files=True)
    assert res.files == {str(tree / "c" / "empty"): 0}


def test_unreadable_directory_is_reported(tree):
    if os.geteuid() == 0:
        pytest.skip("root can read everything")
    locked = tree / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        res = scan(str(tree), excludes=())
        assert res.errors == [str(locked)]
    finally:
        locked.chmod(0o755)


def test_max_depth_only_filters_display(tree):
    res = scan(str(tree), apparent_size=True, excludes=(), include_files=True)
    shallow = select_entries(res, max_depth=1)
    assert {os.path.basename(e.path) for e in shallow} == {"a", "c"}
    assert res.total > 205_000  # the total still includes everything


def test_threshold_and_zero_filters(tree):
    res = scan(str(tree), apparent_size=True, excludes=(), include_files=True)
    big = select_entries(res, threshold=parse_size("100K"))
    assert all(e.size >= 100 * 1024 for e in big)
    assert str(tree / "a" / "b" / "big.bin") in {e.path for e in big}
    small = select_entries(res, threshold=parse_size("-1K"))
    assert all(e.size <= 1024 for e in small)
    assert all(e.size > 0 for e in select_entries(res, exclude_zero=True))


def test_top_and_sort(tree):
    res = scan(str(tree), apparent_size=True, excludes=(), include_files=True)
    top = select_entries(res, top=2)
    assert len(top) == 2 and top[0].size >= top[1].size
    asc = select_entries(res, sort="asc")
    assert [e.size for e in asc] == sorted(e.size for e in asc)


@pytest.mark.parametrize("text, expected", [
    ("100", 100 * 1024), ("1K", 1024), ("100M", 100 * 1024 ** 2), ("1.5G", int(1.5 * 1024 ** 3)),
    ("2GiB", 2 * 1024 ** 3), ("-1G", -(1024 ** 3)), ("10kb", 10 * 1024),
])
def test_parse_size(text, expected):
    assert parse_size(text) == expected


def test_parse_size_invalid():
    with pytest.raises(ValueError):
        parse_size("ten megs")


def test_human_size():
    assert human_size(0) == "      0 B "
    assert human_size(1536) == "    1.5 KB"
    assert human_size(5 * 1024 ** 3) == "    5.0 GB"
    assert len({len(human_size(n)) for n in (1, 2048, 10 ** 12)}) == 1  # fixed width


def run_cli(capsys, *argv):
    with pytest.raises(SystemExit) as exc:
        duBE.main(list(argv))
        raise SystemExit(0)
    out = capsys.readouterr()
    return exc.value.code, out.out, out.err


def test_cli_json(tree, capsys):
    code, out, _ = run_cli(capsys, str(tree), "--json", "--apparent-size", "--max-depth", "1")
    data = json.loads(out)
    assert code == 0 and data["total"] > 205_000
    assert {os.path.basename(e["path"]) for e in data["entries"]} == {"a", "c"}


def test_cli_flat_and_tree_are_plain_when_piped(tree, capsys):
    code, out, _ = run_cli(capsys, str(tree) + "/", "--tree", "-a")
    assert code == 0 and "\033[" not in out
    assert "├── a/" in out and "big.bin" in out and "Total" in out
    code, out, _ = run_cli(capsys, str(tree), "--top", "1")
    assert out.count("%") == 1


def test_cli_errors(tree, capsys):
    code, _, err = run_cli(capsys, str(tree / "missing"))
    assert code == 1 and "Not a directory" in err
    code, _, err = run_cli(capsys, str(tree), "--tree", "--top", "3")
    assert code == 1 and "--top" in err
    code, _, err = run_cli(capsys, str(tree), "--threshold", "lots")
    assert code == 1 and "invalid size" in err
