# Makefile for UW-Automation-Program

.PHONY: help venv install poetry-setup run gui test clean

help:
	@echo "Available targets:"
	@echo "  venv           Create a Python virtual environment (venv)"
	@echo "  install        Install dependencies with pip"
	@echo "  poetry-setup   Install dependencies with Poetry"
	@echo "  run            Run the main GUI application"
	@echo "  gui            Alias for run"
	@echo "  test           Run all tests (if any)"
	@echo "  clean          Remove __pycache__ and .pyc files"

venv:
	python -m venv venv

install:
	. venv/Scripts/activate && pip install -r requirements.txt

poetry-setup:
	pip install poetry
	poetry install

run gui:
	python app.py

test:
	pytest tests/

clean:
	del /s /q __pycache__
	del /s /q *.pyc
