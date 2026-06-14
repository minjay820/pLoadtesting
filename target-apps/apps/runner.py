import importlib
import os

MODULE_NAME = os.getenv("TARGET_APP_MODULE", "echo_api")

app = importlib.import_module(MODULE_NAME).app

