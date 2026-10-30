from diff_utils import added_lines, limit_files, number_patch, should_review, valid_lines

PATCH = "@@ -1,4 +1,5 @@\n import os\n-x = 1\n+x = 2\n+y = 3\n print(x)"


def test_valid_and_added_lines():
    assert valid_lines(PATCH) == {1, 2, 3, 4}
    assert added_lines(PATCH) == {2, 3}


def test_number_patch_labels_new_lines():
    numbered = number_patch(PATCH)
    assert "L2|+x = 2" in numbered
    assert "L1| import os" in numbered
    assert "   |-x = 1" in numbered


def test_should_review():
    assert should_review("src/app.py")
    assert not should_review("package-lock.json")
    assert not should_review("logo.png")
    assert not should_review("README.md")
    assert not should_review("node_modules/x/index.js")
    assert not should_review("static/app.min.js")


def test_limit_files():
    files = [{"patch": "a" * 10}, {"patch": "b" * 10}, {"patch": "c" * 10}]
    included, skipped = limit_files(files, max_chars=25, max_files=10)
    assert len(included) == 2 and skipped == 1
