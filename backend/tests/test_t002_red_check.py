"""Test cố ý thất bại để kiểm chứng branch protection của T-002 (PR đỏ). PR này sẽ được đóng, không merge."""


def test_t002_intentional_failure() -> None:
    assert 1 + 1 == 3
