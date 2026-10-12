import runpy


def test_environment_checker_has_main_guard():
    namespace = runpy.run_path("scripts/check_environment.py", run_name="environment_check_test")
    assert callable(namespace["main"])
