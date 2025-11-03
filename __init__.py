#
# This repository is an Anvil app. Learn more at https://anvil.works/
# To run the server-side code on your own machine, run:
# pip install anvil-uplink
# python -m anvil.run_app_via_uplink YourAppPackageName

try:
	# Extend package search path to support the repository layout used by
	# the original Anvil packaging (server_code / client_code). Guard with
	# try/except so importing as a normal project package doesn't fail in
	# other environments (tests/CI).
	__path__ = [__path__[0] + "/server_code", __path__[0] + "/client_code"]
except Exception:
	# If __path__ is unavailable for any reason, silently continue.
	pass
