.PHONY: first-result test install-ui build-ui reference links
first-result:
	python3 tools/first-estimate.py
test:
	python3 -m unittest discover -s tests -v
install-ui:
	cd frontend && npm ci --ignore-scripts
build-ui:
	cd frontend && npm run typecheck && npm run build
reference:
	python3 tools/source-reference.py
links:
	python3 tools/link-gate.py
