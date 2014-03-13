
TEST_TARGETS =
ITEST_TARGETS = -m integration
UTEST_TARGETS = -m "not(integration)"

all: _tests

integration:
	$(eval TEST_TARGETS := $(ITEST_TARGETS))

unit:
	$(eval TEST_TARGETS := $(UTEST_TARGETS))

utests: test
utest: test
tests: test
test: unit _tests
itests: itest
itest: integration _tests

_tests: py_env
	bash -c 'source py_env/bin/activate && py.test tests $(TEST_TARGETS)'

ucoverage: unit coverage
icoverage: integration coverage

coverage: py_env
	bash -c 'source py_env/bin/activate && \
		coverage erase && \
		coverage run `which py.test` tests $(TEST_TARGETS) && \
		coverage report -m'

py_env: requirements.txt setup.py
	rm -rf py_env
	virtualenv py_env
	bash -c 'source py_env/bin/activate && \
		pip install -e . && \
		pip install -r requirements.txt'

clean:
	rm -rf py_env
