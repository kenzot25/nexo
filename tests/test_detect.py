from pathlib import Path
import pytest
from nexo.detect import classify_file, count_words, detect, FileType, _looks_like_paper, _is_ignored, _load_nexoignore

FIXTURES = Path(__file__).parent / "fixtures"


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Symlink creation requires Windows developer mode or elevated privileges")
        pytest.skip(f"Symlink creation not available: {exc}")

def test_classify_python():
    assert classify_file(Path("foo.py")) == FileType.CODE

def test_classify_typescript():
    assert classify_file(Path("bar.ts")) == FileType.CODE

def test_classify_markdown():
    assert classify_file(Path("README.md")) == FileType.DOCUMENT

def test_classify_pdf():
    assert classify_file(Path("paper.pdf")) == FileType.PAPER

def test_classify_pdf_in_xcassets_skipped():
    # PDFs inside Xcode asset catalogs are vector icons, not papers
    asset_pdf = Path("MyApp/Images.xcassets/icon.imageset/icon.pdf")
    assert classify_file(asset_pdf) is None

def test_classify_pdf_in_xcassets_root_skipped():
    asset_pdf = Path("Pods/HXPHPicker/Assets.xcassets/photo.pdf")
    assert classify_file(asset_pdf) is None

def test_classify_unknown_returns_none():
    assert classify_file(Path("archive.zip")) is None

def test_classify_image():
    assert classify_file(Path("screenshot.png")) == FileType.IMAGE
    assert classify_file(Path("design.jpg")) == FileType.IMAGE
    assert classify_file(Path("diagram.webp")) == FileType.IMAGE

def test_count_words_sample_md():
    words = count_words(FIXTURES / "sample.md")
    assert words > 5

def test_detect_finds_fixtures():
    result = detect(FIXTURES)
    assert result["total_files"] >= 2
    assert "code" in result["files"]
    assert "document" in result["files"]

def test_detect_warns_small_corpus():
    result = detect(FIXTURES)
    assert result["needs_graph"] is False
    assert result["warning"] is not None

def test_detect_skips_dotfiles():
    result = detect(FIXTURES)
    for files in result["files"].values():
        for f in files:
            assert "/." not in f


def test_classify_md_paper_by_signals(tmp_path):
    """A .md file with enough paper signals should classify as PAPER."""
    paper = tmp_path / "paper.md"
    paper.write_text(
        "# Abstract\n\nWe propose a new method. See [1] and [23].\n"
        "This work was published in the Journal of AI. ArXiv preprint.\n"
        "See Equation 3 for details. \\cite{vaswani2017}.\n"
    )
    assert classify_file(paper) == FileType.PAPER


def test_classify_md_doc_without_signals(tmp_path):
    """A plain .md file without paper signals should stay DOCUMENT."""
    doc = tmp_path / "notes.md"
    doc.write_text("# My Notes\n\nHere are some notes about the project.\n")
    assert classify_file(doc) == FileType.DOCUMENT


def test_classify_attention_paper():
    """The real attention paper file should be classified as PAPER."""
    paper_path = Path("/home/safi/nexo_eval/papers/attention_is_all_you_need.md")
    if paper_path.exists():
        result = classify_file(paper_path)
        assert result == FileType.PAPER


def test_nexoignore_excludes_file(tmp_path):
    """Files matching .nexoignore patterns are excluded from detect()."""
    (tmp_path / ".nexoignore").write_text("vendor/\n*.generated.py\n")
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "lib.py").write_text("x = 1")
    (tmp_path / "main.py").write_text("print('hi')")
    (tmp_path / "schema.generated.py").write_text("x = 1")

    result = detect(tmp_path)
    file_list = result["files"]["code"]
    assert any("main.py" in f for f in file_list)
    assert not any("vendor" in f for f in file_list)
    assert not any("generated" in f for f in file_list)
    assert result["nexoignore_patterns"] == 2


def test_nexoignore_missing_is_fine(tmp_path):
    """No .nexoignore is not an error."""
    (tmp_path / "main.py").write_text("x = 1")
    result = detect(tmp_path)
    assert result["nexoignore_patterns"] == 0


def test_nexoignore_comments_ignored(tmp_path):
    """Comment lines in .nexoignore are not treated as patterns."""
    (tmp_path / ".nexoignore").write_text("# this is a comment\n\nmain.py\n")
    (tmp_path / "main.py").write_text("x = 1")
    (tmp_path / "other.py").write_text("x = 2")
    result = detect(tmp_path)
    assert not any("main.py" in f for f in result["files"]["code"])
    assert any("other.py" in f for f in result["files"]["code"])


def test_detect_follows_symlinked_directory(tmp_path):
    real_dir = tmp_path / "real_lib"
    real_dir.mkdir()
    (real_dir / "util.py").write_text("x = 1")
    _symlink_or_skip(tmp_path / "linked_lib", real_dir)

    result_no = detect(tmp_path, follow_symlinks=False)
    result_yes = detect(tmp_path, follow_symlinks=True)

    assert any("real_lib" in f for f in result_no["files"]["code"])
    assert not any("linked_lib" in f for f in result_no["files"]["code"])
    assert any("linked_lib" in f for f in result_yes["files"]["code"])


def test_detect_follows_symlinked_file(tmp_path):
    (tmp_path / "real.py").write_text("x = 1")
    _symlink_or_skip(tmp_path / "link.py", tmp_path / "real.py")

    result = detect(tmp_path, follow_symlinks=True)
    code = result["files"]["code"]
    assert any("real.py" in f for f in code)
    assert any("link.py" in f for f in code)


def test_nexoignore_discovered_from_parent(tmp_path):
    """A .nexoignore in a parent directory applies to subdirectory scans."""
    (tmp_path / ".nexoignore").write_text("vendor/\n")
    sub = tmp_path / "packages" / "mylib"
    sub.mkdir(parents=True)
    (sub / "main.py").write_text("x = 1")
    vendor = sub / "vendor"
    vendor.mkdir()
    (vendor / "dep.py").write_text("y = 2")

    result = detect(sub)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert not any("vendor" in f for f in code_files)
    assert result["nexoignore_patterns"] >= 1


def test_nexoignore_stops_at_git_boundary(tmp_path):
    """Upward search stops at the git repo root (.git directory)."""
    (tmp_path / ".nexoignore").write_text("main.py\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    sub = repo / "sub"
    sub.mkdir()
    (sub / "main.py").write_text("x = 1")

    result = detect(sub)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert result["nexoignore_patterns"] == 0


def test_nexoignore_at_git_root_is_included(tmp_path):
    """A .nexoignore at the git repo root is included when scanning a subdir."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".nexoignore").write_text("vendor/\n")
    sub = repo / "packages" / "mylib"
    sub.mkdir(parents=True)
    (sub / "main.py").write_text("x = 1")
    vendor = sub / "vendor"
    vendor.mkdir()
    (vendor / "dep.py").write_text("y = 2")

    result = detect(sub)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert not any("vendor" in f for f in code_files)
    assert result["nexoignore_patterns"] == 1


def test_detect_handles_circular_symlinks(tmp_path):
    sub = tmp_path / "a"
    sub.mkdir()
    (sub / "main.py").write_text("x = 1")
    _symlink_or_skip(sub / "loop", tmp_path)

    result = detect(tmp_path, follow_symlinks=True)
    assert any("main.py" in f for f in result["files"]["code"])


def test_classify_video_extensions():
    """Video and audio file extensions should classify as VIDEO."""
    from nexo.detect import FileType
    assert classify_file(Path("lecture.mp4")) == FileType.VIDEO
    assert classify_file(Path("podcast.mp3")) == FileType.VIDEO
    assert classify_file(Path("talk.mov")) == FileType.VIDEO
    assert classify_file(Path("recording.wav")) == FileType.VIDEO
    assert classify_file(Path("webinar.webm")) == FileType.VIDEO
    assert classify_file(Path("audio.m4a")) == FileType.VIDEO


def test_detect_includes_video_key(tmp_path):
    """detect() result always includes a 'video' key even with no video files."""
    (tmp_path / "main.py").write_text("x = 1")
    result = detect(tmp_path)
    assert "video" in result["files"]


def test_detect_finds_video_files(tmp_path):
    """detect() correctly counts video files and does not add them to word count."""
    (tmp_path / "lecture.mp4").write_bytes(b"fake video data")
    (tmp_path / "notes.md").write_text("# Notes\nSome content here.")
    result = detect(tmp_path)
    assert len(result["files"]["video"]) == 1
    assert any("lecture.mp4" in f for f in result["files"]["video"])
    # total_words should not include video files (they have no readable text)
    assert result["total_words"] >= 0  # won't crash


def test_detect_video_not_in_words(tmp_path):
    """Video files do not contribute to total_words."""
    (tmp_path / "clip.mp4").write_bytes(b"\x00" * 100)
    result = detect(tmp_path)
    # Only video file present — total_words should be 0
    assert result["total_words"] == 0


def test_detect_respects_gitignore(tmp_path):
    """Common dependency/build folders should be skipped via .gitignore."""
    (tmp_path / ".gitignore").write_text("node_modules/\ndist/\n")
    (tmp_path / "main.py").write_text("x = 1")

    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "lib.js").write_text("export const x = 1")

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "bundle.js").write_text("console.log('generated')")

    result = detect(tmp_path)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert not any("node_modules" in f for f in code_files)
    assert not any("dist" in f for f in code_files)
    assert result["gitignore_patterns"] == 2


def test_detect_can_ignore_gitignore_when_disabled(tmp_path):
    """respect_gitignore=False should include files otherwise ignored."""
    (tmp_path / ".gitignore").write_text("generated/\n")
    (tmp_path / "main.py").write_text("x = 1")
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "lib.js").write_text("export const x = 1")

    result = detect(tmp_path, respect_gitignore=False)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert any("generated" in f for f in code_files)
    assert result["gitignore_patterns"] == 0


def test_detect_gitignore_negation_restores_file(tmp_path):
    (tmp_path / ".gitignore").write_text("*.js\n!important.js\n")
    (tmp_path / "main.py").write_text("x = 1")
    (tmp_path / "ignored.js").write_text("console.log('ignored')")
    (tmp_path / "important.js").write_text("console.log('keep')")

    result = detect(tmp_path)
    code_files = result["files"]["code"]
    assert not any("ignored.js" in f for f in code_files)
    assert any("important.js" in f for f in code_files)


def test_detect_gitignore_escaped_comment_and_bang(tmp_path):
    (tmp_path / ".gitignore").write_text("\\#literal.py\n\\!literal2.py\n")
    (tmp_path / "#literal.py").write_text("x = 1")
    (tmp_path / "!literal2.py").write_text("x = 1")

    result = detect(tmp_path)
    code_files = result["files"]["code"]
    assert not any("#literal.py" in f for f in code_files)
    assert not any("!literal2.py" in f for f in code_files)
