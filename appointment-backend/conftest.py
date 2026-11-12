# test_sms.py sends a real SMS on import, so pytest must not collect it.
# test_mysql.py is intentionally NOT ignored: it holds the terminal-state
# guard regression tests.
collect_ignore = ["test_sms.py"]
