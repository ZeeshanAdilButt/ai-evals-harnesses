import pytest


def test_register_and_get_by_name(impl1):
    @impl1.register_grader("always-true-for-test")
    def always(output, case):
        return True

    assert impl1.get_grader("always-true-for-test") is always


def test_decorator_returns_the_function(impl1):
    def grader(output, case):
        return False

    assert impl1.register_grader("returns-fn-for-test")(grader) is grader


def test_unknown_grader_message(impl1):
    with pytest.raises(impl1.UnknownGrader, match="no grader named nope"):
        impl1.get_grader("nope")


def test_shipped_graders_are_registered(impl1):
    case = {"expected": {"category": "refund", "urgent": False}}
    assert impl1.get_grader("match")('{"category": "Refund", "urgent": false}', case) is True
    assert impl1.get_grader("exact")('{"category": "Refund", "urgent": false}', case) is False
