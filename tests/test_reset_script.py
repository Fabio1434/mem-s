import runpy


def test_reset_script_main_is_import_safe():
    namespace = runpy.run_path("scripts/reset_lab_data.py", run_name="reset_script_test")
    assert callable(namespace["main"])
